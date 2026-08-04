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
| GET | `/overview` | Executive dashboard |
| GET | `/morning-brief` | The full briefing |
| POST | `/morning-brief/regenerate` | Re-run generation against the latest data |
| PATCH | `/morning-brief/checklist/{item_id}` | Mark a checklist item done |
| GET | `/inbox` | Categorised, summarised threads |
| GET | `/meetings` | Meeting intelligence for today |
| GET | `/meetings/{meeting_id}` | A single meeting |
| GET | `/crm` | Pipeline with executive-attention filtering |
| GET | `/ask` | Suggested questions and recent history |
| POST | `/ask` | Answer a question as a cited report |
| GET | `/integrations` | Connection status and sync history |
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
| `OverviewService` | Dashboard aggregation |
| `MorningBriefService` | Brief assembly, regeneration, checklist state |
| `InboxService` | Thread categorisation and counts |
| `MeetingService` | Meeting intelligence and scheduling maths |
| `CRMService` | Pipeline filtering, weighting and exposure |
| `AskService` | Question matching and cited report construction |
| `IntegrationService` | Connection state and sync triggers |
| `SettingsService` | Profile, preferences, notifications, security |

## Database Models

| Model | Purpose |
|-------|---------|
| `User` | Executive profile and briefing preferences |
| `MorningBrief` | One generated briefing |
| `BriefAction` | Checklist item — the only brief state the user edits |
| `Meeting` | Calendar event plus generated preparation |
| `Email` | Thread with summary, priority and suggested response |
| `Opportunity` | Pipeline opportunity with risk assessment |
| `Integration` | Connected provider, scopes and tokens |
| `SyncEvent` | Audit trail of every read from a connected system |

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

Connection pooling is configured in `db/session.py` (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`).

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
