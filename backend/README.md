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

**Request flow:** Route → Service → curated data (later: database and integrations)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/workspace` | Shell payload: identity, brief freshness, nav counts |
| GET | `/overview` | Executive dashboard (summary/priorities/risks partially DB-backed — see below) |
| GET | `/daily-brief/latest` | Latest `DailyBrief` row, read directly from PostgreSQL |
| GET | `/morning-brief` | The full briefing |
| POST | `/morning-brief/regenerate` | Re-run generation against the latest data |
| PATCH | `/morning-brief/checklist/{item_id}` | Mark a checklist item done |
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
| `WorkspaceService` | Shell identity and navigation counts |
| `OverviewService` | Dashboard aggregation — reads `summary`/`priorities`/`risks` from `DailyBriefService`, falls back to curated data |
| `DailyBriefService` | First table backed by real PostgreSQL reads/writes: `create_brief()`, `get_latest_brief()`, `get_brief_by_id()` |
| `MorningBriefService` | Brief assembly, regeneration, checklist state |
| `InboxService` | Thread categorisation and counts — reads `emails` from PostgreSQL, falls back to curated data (Phase 3 of the migration) |
| `MeetingService` | Meeting intelligence and scheduling maths — reads `meetings` from PostgreSQL, falls back to curated data (Phase 2 of the migration) |
| `CRMService` | Pipeline filtering, weighting and exposure — reads `opportunities` from PostgreSQL, falls back to curated data (Phase 4 of the migration) |
| `AskService` | Question matching and cited report construction |
| `IntegrationService` | Connection state and sync triggers — reads `integrations` from PostgreSQL, falls back to curated data (Phase 5 of the migration) |
| `SettingsService` | Profile, preferences, notifications, security |

## Database Models

| Model | Purpose |
|-------|---------|
| `User` | Executive profile and briefing preferences |
| `MorningBrief` | One generated briefing |
| `BriefAction` | Checklist item — the only brief state the user edits |
| `Meeting` | Calendar event plus generated preparation — backs `GET /meetings` (Phase 2 of the migration) |
| `Email` | Thread with summary, priority and suggested response — backs `GET /inbox` (Phase 3 of the migration) |
| `Opportunity` | Pipeline opportunity with risk assessment — backs `GET /crm` (Phase 4 of the migration) |
| `Integration` | Connected provider, scopes and tokens — backs `GET /integrations` (Phase 5 of the migration) |
| `SyncEvent` | Audit trail of every read from a connected system |
| `DailyBrief` | Phase 1 of the PostgreSQL migration — `summary`/`priorities`/`risks` for `OverviewService`, plus `recommendations`/`executive_score` reserved for later |

## Local Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

The API serves curated data and does not touch PostgreSQL yet, so no database is required to run it locally.

### PostgreSQL (for schema work)

```bash
docker run --name briefly-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=briefly \
  -p 5432:5432 -d postgres:16

alembic upgrade head
```

Connection pooling is configured in `db/session.py` (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`, and a 5s `connect_timeout` so a down database fails fast instead of hanging a request).

### Seeding a DailyBrief

Once the `daily_briefs` table exists (after running your migration):

```bash
python scripts/seed_daily_brief.py
```

Inserts one realistic briefing so `/overview` and `/daily-brief/latest` have something real to read instead of falling back to curated data.

### Seeding Meetings

Once the `meetings` table matches `app.models.Meeting` (after running your migration):

```bash
python scripts/seed_meetings.py
```

Inserts five realistic meetings (Board Meeting, Investor Update, Customer Success Review, Product Roadmap, Hiring Interview) for a demo user, so `/meetings` has something real to read instead of falling back to curated data. Safe to re-run — it skips titles it already seeded.

### Seeding Emails

Once the `emails` table matches `app.models.Email` (after running your migration):

```bash
python scripts/seed_emails.py
```

Inserts five realistic emails (a board communication, an investor update, a customer request, an internal announcement and a hiring/recruiting email) for a demo user, so `/inbox` has something real to read instead of falling back to curated data. Safe to re-run — it skips subjects it already seeded.

### Seeding Opportunities

Once the `opportunities` table matches `app.models.Opportunity` (after running your migration):

```bash
python scripts/seed_opportunities.py
```

Inserts five realistic opportunities (an enterprise SaaS renewal, a new customer acquisition, an expansion, a strategic partnership and an upsell) for a demo user, so `/crm` has something real to read instead of falling back to curated data. Safe to re-run — it skips company/stage pairs it already seeded.

### Seeding Integrations

Once the `integrations` table matches `app.models.Integration` (after running your migration):

```bash
python scripts/seed_integrations.py
```

Inserts five realistic integrations (Google Calendar, Gmail and Notion connected; Slack not connected; GoHighLevel mid-sync) for a demo user, so `/integrations` has something real to read instead of falling back to curated data. Safe to re-run — it skips providers it already seeded. Only display metadata (name/category/description/metrics/poweredBy) and connection status are stored — no real OAuth tokens.

### Tests

```bash
pytest tests/ -v
```

## Railway Deployment

1. Create a Railway project with the **PostgreSQL** plugin.
2. Add a Python service pointing at `backend/`.
3. Set environment variables:
   - `DATABASE_URL` — provided by the PostgreSQL plugin
   - `CORS_ORIGINS` — your frontend URL
   - `ENVIRONMENT=production`, `DEBUG=false`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Deploy hook: `alembic upgrade head`

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
