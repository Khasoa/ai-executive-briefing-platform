# Briefly Backend

FastAPI backend for Briefly — the AI Executive Briefing Platform.

## Overview

This service assembles the Morning Brief and every view that supports it. Persistence-backed domains read PostgreSQL first and fall back to `demo_data` when a table is empty or unreachable. Response shapes already match what live integrations will return, so the frontend contract is final. Adding a live provider means implementing one module in `app/integrations/` — routes, schemas and the frontend stay untouched.

## Architecture

```
app/
├── main.py           # Application factory: CORS, logging, router registration
├── api/
│   ├── deps.py       # DI: database session + get_current_user
│   └── routes/       # HTTP handlers — thin, no business logic
├── core/
│   ├── config.py     # pydantic-settings configuration
│   ├── security.py   # Password hashing + JWT helpers
│   └── logging.py    # Logging setup
├── db/
│   ├── base.py       # SQLAlchemy declarative base
│   └── session.py    # Engine, session factory, get_db()
├── middleware/
│   └── logging.py    # Per-request method, path, status and duration
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic request/response contracts
├── services/         # Business logic
└── integrations/     # External API clients (future)
```

**Request flow:** Route → Service → PostgreSQL (with `demo_data` fallback) → future integration modules

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/auth/register` | Create password account + tokens |
| POST | `/auth/login` | Password login + tokens |
| POST | `/auth/refresh` | Rotate refresh token |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/me` | Current user (Bearer or demo fallback) |
| GET | `/auth/oauth/{provider}/start` | Begin OAuth (`google`, `notion`, `gohighlevel`) |
| GET | `/auth/oauth/{provider}/callback` | Provider redirect; tokens or ticket redirect |
| POST | `/auth/oauth/{provider}/exchange` | Exchange one-time OAuth ticket for tokens |
| GET | `/auth/oauth/{provider}/status` | Connection status |
| POST | `/auth/oauth/{provider}/refresh` | Refresh / return provider access token |
| POST | `/auth/oauth/{provider}/disconnect` | Clear stored provider tokens |
| POST | `/webhooks/n8n/run` | n8n orchestration (secret header) |
| POST | `/webhooks/n8n/daily` | Sync providers + Morning Brief |
| POST | `/webhooks/n8n/weekly` | Sync providers + Weekly Digest |
| GET | `/workspace` | Shell payload: identity, brief freshness, nav counts |
| GET | `/overview` | Executive dashboard (summary/priorities/risks partially DB-backed — see below) |
| GET | `/daily-brief/latest` | Latest `DailyBrief` row, read directly from PostgreSQL |
| GET | `/morning-brief` | The full briefing (DB-backed — see below) |
| POST | `/morning-brief/regenerate` | Create/replace today's brief from the current generator (DB-backed) |
| PATCH | `/morning-brief/checklist/{item_id}` | Mark a checklist item done (DB-backed) |
| GET | `/inbox` | Categorised, summarised threads (partially DB-backed — see below) |
| GET | `/meetings` | Meeting intelligence for today (partially DB-backed — see below) |
| GET | `/meetings/{meeting_id}` | A single meeting |
| GET | `/crm` | Pipeline with executive-attention filtering (partially DB-backed — see below) |
| GET | `/ask` | Suggested questions and recent history |
| POST | `/ask` | Answer a question as a cited report |
| GET | `/integrations` | Connection status and sync history (connection status partially DB-backed — see below) |
| POST | `/integrations/{id}/sync` | Trigger a manual read |
| GET | `/settings` | Profile, preferences, notifications, security, theme |
| PATCH | `/settings/preferences` | Partial preference update |
| PATCH | `/settings/notifications/{id}` | Toggle a notification |

Full request and response documentation: [docs/api.md](../docs/api.md).

There is deliberately no send, move or accept endpoint. See ADR-002.

## Services

| Service | Domain ownership |
|---------|------------------|
| `AuthService` | Register, login, refresh rotation, logout, access-token resolution, `issue_tokens` |
| `OAuthService` | Provider authorize/callback, find-or-create user, encrypted token storage, provider refresh |
| `CalendarSyncService` | Incremental Google Calendar → `Meeting` sync (webhook + manual) |
| `GmailSyncService` | Incremental Gmail → `Email` sync (webhook + manual); leaves AI fields empty |
| `AIService` | Sole OpenAI orchestration (Morning Brief, meeting prep, email summary, Ask) |
| `WorkspaceService` | Shell identity, nav badges, brief freshness (via `MorningBriefService.get_brief_meta()`) |
| `OverviewService` | Dashboard aggregation — DailyBrief summary slice + MeetingService prep list + brief meta |
| `DailyBriefService` | `daily_briefs` reads/writes |
| `MorningBriefService` | `morning_briefs` / `brief_actions` — AI generation + curated failover, checklist |
| `InboxService` | `emails` — lazy AI summary on detail when fields empty |
| `MeetingService` | `meetings` — lazy AI prep on detail when intelligence empty |
| `CRMService` | `opportunities` (incl. GoHighLevel-synced deals) |
| `GHLSyncService` | GoHighLevel opportunities → `Opportunity` (idempotent `external_id`) |
| `MondaySyncService` | monday.com boards/items → `WorkItem` |
| `ClickUpSyncService` | ClickUp tasks → `WorkItem` |
| `WorkItemService` | Provider-neutral work-item reads for Overview / AI |
| `AskService` | Cited reports via `AIService` + curated failover; persists `ask_reports` |
| `IntegrationService` | Canonical catalog ∪ user `integrations` + `sync_events` |
| `OrchestrationService` | n8n-driven multi-provider sync + brief/digest regenerate |
| `SettingsService` | Profile from `User`; demo preferences curated; non-demo preferences on `User.preferences` |

Shared infrastructure: `db_fallback.py` (empty-table + `SQLAlchemyError` fallback with session rollback), `mapping_utils.py` (id/JSONB/relative-time helpers), `demo_user.py` (demo tenant + `AUTH_REQUIRED=false` fallback). Domain services take `(db, user)` and own their tables; cross-domain reads always go through the owning service, never through another service's mock collection.

Demo mode: with `AUTH_REQUIRED=false` (default), missing Bearer credentials resolve to Lydia's demo user so the portfolio demo is unchanged. Set `AUTH_REQUIRED=true` and a strong `SECRET_KEY` before multi-user production.

## Database Models

| Model | Purpose |
|-------|---------|
| `User` | Executive profile, optional password hash, briefing preferences |
| `RefreshToken` | Hashed opaque refresh tokens (revocable, rotating) |
| `OAuthState` | CSRF state for Authorization Code Flow |
| `OAuthLoginTicket` | One-time ticket after OAuth callback redirect |
| `MorningBrief` | One generated briefing — backs `GET /morning-brief` (Phase 7 of the migration, the final one) |
| `BriefAction` | Checklist item — the only brief state the user edits — backs `PATCH /morning-brief/checklist/{item_id}` (Phase 7) |
| `Meeting` | Calendar event plus generated preparation — backs `GET /meetings` (Phase 2 of the migration) |
| `Email` | Thread with summary, priority and suggested response — backs `GET /inbox` (Phase 3 of the migration) |
| `Opportunity` | Pipeline opportunity with risk assessment — backs `GET /crm` (Phase 4 of the migration) |
| `Integration` | Connected provider, scopes and tokens — backs `GET /integrations` (Phase 5 of the migration) |
| `SyncEvent` | Sync audit trail — backs `syncHistory` on `GET /integrations` |
| `DailyBrief` | Overview summary slice — `summary`/`priorities`/`risks` (+ reserved `recommendations`/`executive_score`) |
| `AskReport` | Persisted Ask Briefly answers (conversation history) |

## OpenAI

Set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`, `OPENAI_EMBED_MODEL`, `OPENAI_TIMEOUT_SECONDS`). Services never call OpenAI HTTP directly — they use `AIService`, which wraps `app/integrations/openai.py` (Responses API).

When the key is missing, or the provider times out / rate-limits / returns malformed JSON, every capability falls back to the existing curated/`demo_data` behaviour. Today's `MorningBrief` row is the generation cache; `POST /morning-brief/regenerate` forces a new call.

## Local Setup / Developer Onboarding

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### PostgreSQL

```bash
docker run --name briefly-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=briefly \
  -p 5432:5432 -d postgres:16

# Point DATABASE_URL in .env at that instance, then:
alembic upgrade head
```

Connection pooling lives in `db/session.py` (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, 5s `connect_timeout`).

Migration history, Atlas→Briefly upgrade path, and data-safety rules: [docs/migrations.md](../docs/migrations.md).

### Seed everything (idempotent)

```bash
python3 scripts/seed.py
```

That single entry point runs every domain seed in dependency order (daily brief → meetings → emails → opportunities → integrations → sync events → morning brief). Individual `scripts/seed_*.py` modules remain available for modular re-runs.

Shared helpers live in `scripts/seed_common.py` (`get_or_create_demo_user`, `seed_idempotently`). Every seed is safe to re-run.

Without a database (or when a table is empty / unreachable), services fall back to `demo_data.py` so the API stays usable.

### Run

```bash
uvicorn app.main:app --reload --port 8000
pytest tests/ -v
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

## Production Setup (Railway)

1. PostgreSQL plugin + Python service pointing at `backend/`.
2. Environment: `DATABASE_URL`, `CORS_ORIGINS`, `ENVIRONMENT=production`, `DEBUG=false`, a strong `SECRET_KEY`, and usually `AUTH_REQUIRED=true`.
3. Deploy hook: `alembic upgrade head` (applies through `012`).
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. One-time seed (or CI step): `python3 scripts/seed.py`
6. Optional: `OPENAI_API_KEY` for live generation (blank = curated failover). OpenAI is API-key based — Integrations shows Configured / API key required (never an OAuth Connect flow).
7. Optional: `NOTION_CLIENT_*`, `GHL_CLIENT_*`, `MONDAY_CLIENT_*`, `CLICKUP_CLIENT_*`, `N8N_WEBHOOK_SECRET` (shared webhook secret — not OAuth).
8. For Google Calendar/Gmail sync, enable Calendar API and Gmail API in the Google Cloud Console project that owns `GOOGLE_CLIENT_ID`.

If an environment was previously stamped `001` on Atlas tables, `003` aligns it without rewriting revision history — see [docs/migrations.md](../docs/migrations.md).

## Integration Roadmap

| Provider | Service | Target |
|----------|---------|--------|
| Google Calendar | `MeetingService` | v1.1 (sync done) |
| Gmail | `InboxService`, `MorningBriefService` | v1.2 (sync done) |
| OpenAI | `AIService` → Brief / Meetings / Inbox / Ask | v1.0.5 (done) |
| Notion | `NotionSyncService` → Overview / Morning Brief / Ask | v1.0.6 (done) |
| GoHighLevel | `GHLSyncService` → `CRMService` / AI | v1.4 (done) |
| n8n | `OrchestrationService` webhooks | v1.5 (done) |
| monday.com | `MondaySyncService` → `WorkItemService` / AI | v1.6 (done) |
| ClickUp | `ClickUpSyncService` → `WorkItemService` / AI | v1.6 (done) |

See [docs/roadmap.md](../docs/roadmap.md).
