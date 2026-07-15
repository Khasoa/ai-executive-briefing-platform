# Relay Backend

FastAPI backend for Relay — AI Executive Partner.

## Overview

This backend provides a REST API for the Relay executive dashboard. In v0.1, all endpoints return realistic mock data structured to match the React frontend. The architecture is designed so external integrations (Gmail, Google Calendar, GoHighLevel, OpenAI, etc.) can be plugged in later without changing the API contract.

## Architecture

```
app/
├── main.py           # FastAPI application factory
├── api/
│   ├── deps.py       # Dependency injection (database session)
│   └── routes/       # HTTP route handlers (thin layer)
├── core/
│   ├── config.py     # Settings from environment variables
│   └── logging.py    # Logging configuration
├── db/
│   ├── base.py       # SQLAlchemy declarative base
│   └── session.py    # Engine, session factory, get_db()
├── middleware/
│   └── logging.py    # Request logging middleware
├── models/           # SQLAlchemy ORM models
├── schemas/          # Pydantic request/response models
├── services/         # Business logic (mock data now, integrations later)
├── integrations/     # External API clients (placeholder)
└── utils/            # Shared utilities
```

**Request flow:** Route → Service → (Mock Data | Database | Integration)

Routes are thin. Services own business logic. Integrations will wrap third-party APIs.

## Local Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 15+ (local or Docker)

### Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### PostgreSQL (Local)

```bash
# Docker
docker run --name relay-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=relay \
  -p 5432:5432 -d postgres:16

# Run migrations
alembic upgrade head
```

### Run Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Run Tests

```bash
pytest tests/ -v
```

## Railway Deployment

1. Create a new Railway project with a **PostgreSQL** plugin.
2. Add a **Python** service pointing to `backend/`.
3. Set environment variables:
   - `DATABASE_URL` — provided automatically by Railway PostgreSQL
   - `CORS_ORIGINS` — your frontend URL (e.g. `https://relay.example.com`)
   - `ENVIRONMENT=production`
   - `DEBUG=false`
4. Set the start command:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. Run migrations as a deploy hook or one-off command:
   ```
   alembic upgrade head
   ```

## PostgreSQL Configuration

Connection is configured via the `DATABASE_URL` environment variable:

```
postgresql://user:password@host:port/database
```

SQLAlchemy is configured with connection pooling (`pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`).

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/overview` | Executive dashboard data |
| GET | `/overview/daily-brief` | Daily executive briefing |
| GET | `/calendar` | Today's meetings |
| GET | `/inbox` | AI-classified emails |
| GET | `/crm` | CRM pipeline |
| GET | `/projects` | Active projects |
| GET | `/research` | Business intelligence |
| GET | `/assistant` | Chat suggestions and history |
| POST | `/assistant/chat` | Send a message to the AI assistant |
| GET | `/settings` | User settings and integrations |

See [docs/api.md](../docs/api.md) for full documentation.

## Database Models

| Model | Purpose |
|-------|---------|
| `User` | Executive user profile |
| `DailyBrief` | AI-generated daily briefing |
| `Meeting` | Calendar events |
| `Email` | Classified inbox messages |
| `CRMDeal` | Sales pipeline deals |
| `Task` | Projects and initiatives |
| `ResearchItem` | Curated business intelligence |
| `Integration` | Connected third-party services |

## Future Integrations Roadmap

| Integration | Service | Status |
|-------------|---------|--------|
| Google Calendar | `CalendarService` | Planned v0.2 |
| Gmail | `InboxService` | Planned v0.3 |
| GoHighLevel | `CRMService` | Planned v0.4 |
| OpenAI | `AssistantService`, `OverviewService` | Planned v0.5 |
| Make.com | All services (orchestration) | Planned v0.6 |
| ClickUp | `ProjectService` | Planned v0.6 |
| Notion | `ResearchService` | Planned v1.0 |

Integration modules will live in `app/integrations/` and be called from service classes.

## Folder Reference

| Folder | Responsibility |
|--------|---------------|
| `app/api/routes/` | HTTP endpoints only — no business logic |
| `app/services/` | Business logic and data aggregation |
| `app/models/` | Database table definitions |
| `app/schemas/` | API request/response validation |
| `app/integrations/` | Third-party API wrappers (future) |
| `alembic/` | Database migration scripts |
| `tests/` | API and unit tests |
