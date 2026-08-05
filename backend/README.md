# Briefly Backend

FastAPI backend for Briefly — the AI Executive Briefing Platform.

## Overview

This service assembles the Morning Brief and every view that supports it. Endpoints currently return curated data shaped exactly like the responses the integrations will produce, so the frontend contract is already final. Adding a live provider means implementing one module in `app/integrations/` — routes, schemas and the frontend stay untouched.

## Architecture

```
app/
├── main.py           # Application factory: CORS, logging, router registration
├── api/
│   ├── deps.py       # Dependency injection (database session)
│   └── routes/       # HTTP handlers — thin, no business logic
├── core/
│   ├── config.py     # pydantic-settings configuration
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

**Request flow:** Route → Service → PostgreSQL (with `mock_data` fallback) → future integration modules

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
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

| Service | Domain |
|---------|--------|
| Service | Domain ownership |
|---------|------------------|
| `WorkspaceService` | Shell identity, nav badges, brief freshness (via `MorningBriefService.get_brief_meta()`) |
| `OverviewService` | Dashboard aggregation — DailyBrief summary slice + MeetingService prep list + brief meta |
| `DailyBriefService` | `daily_briefs` reads/writes |
| `MorningBriefService` | `morning_briefs` / `brief_actions` — assembly, regenerate, checklist |
| `InboxService` | `emails` |
| `MeetingService` | `meetings` |
| `CRMService` | `opportunities` |
| `AskService` | Cited report construction (curated answers until OpenAI); connected sources via `IntegrationService` |
| `IntegrationService` | `integrations` + `sync_events` |
| `SettingsService` | Profile/preferences (still curated — waits on auth/`User` preferences) |

Shared infrastructure: `db_fallback.py` (empty-table + `SQLAlchemyError` fallback with session rollback), `mapping_utils.py` (id/JSONB/relative-time helpers), `demo_user.py` (single-tenant demo user). Domain services own their tables; cross-domain reads always go through the owning service, never through another service's mock collection.

## Database Models

| Model | Purpose |
|-------|---------|
| `User` | Executive profile and briefing preferences |
| `MorningBrief` | One generated briefing — backs `GET /morning-brief` (Phase 7 of the migration, the final one) |
| `BriefAction` | Checklist item — the only brief state the user edits — backs `PATCH /morning-brief/checklist/{item_id}` (Phase 7) |
| `Meeting` | Calendar event plus generated preparation — backs `GET /meetings` (Phase 2 of the migration) |
| `Email` | Thread with summary, priority and suggested response — backs `GET /inbox` (Phase 3 of the migration) |
| `Opportunity` | Pipeline opportunity with risk assessment — backs `GET /crm` (Phase 4 of the migration) |
| `Integration` | Connected provider, scopes and tokens — backs `GET /integrations` (Phase 5 of the migration) |
| `SyncEvent` | Sync audit trail — backs `syncHistory` on `GET /integrations` |
| `DailyBrief` | Overview summary slice — `summary`/`priorities`/`risks` (+ reserved `recommendations`/`executive_score`) |

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
python scripts/seed_daily_brief.py
python scripts/seed_meetings.py
python scripts/seed_emails.py
python scripts/seed_opportunities.py
python scripts/seed_integrations.py
python scripts/seed_sync_events.py   # requires integrations first
python scripts/seed_morning_brief.py
```

Shared helpers live in `scripts/seed_common.py` (`get_or_create_demo_user`, `seed_idempotently`). Every seed is safe to re-run.

Without a database (or when a table is empty / unreachable), services fall back to `mock_data.py` so the API stays usable.

### Run

```bash
uvicorn app.main:app --reload --port 8000
pytest tests/ -v
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

## Production Setup (Railway)

1. PostgreSQL plugin + Python service pointing at `backend/`.
2. Environment: `DATABASE_URL`, `CORS_ORIGINS`, `ENVIRONMENT=production`, `DEBUG=false`.
3. Deploy hook: `alembic upgrade head` (applies `001`→`002`→`003`).
4. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. One-time seed (or CI step) using the scripts above.

If an environment was previously stamped `001` on Atlas tables, `003` aligns it without rewriting revision history — see [docs/migrations.md](../docs/migrations.md).

## Integration Roadmap

| Provider | Service | Target |
|----------|---------|--------|
| Google Calendar | `MeetingService` | v1.1 |
| Gmail | `InboxService`, `MorningBriefService` | v1.2 |
| OpenAI | `MorningBriefService`, `AskService` | v1.3 |
| GoHighLevel | `CRMService` | v1.4 |
| Notion | `OverviewService`, `MorningBriefService` | v1.4 |
| n8n | Scheduled generation | v1.5 |

See [docs/roadmap.md](../docs/roadmap.md).
