# Relay Architecture

## Overview

Relay is a full-stack SaaS application that gives executives a single AI-powered workspace for email, calendar, CRM, projects, research, and daily briefings. The system is designed as a modular monolith: one deployable backend with clear internal boundaries that can evolve into microservices if needed.

```
┌─────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  Overview · Daily Brief · Inbox · Calendar · CRM · etc.   │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API (JSON)
┌──────────────────────────▼──────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐ │
│  │ Routes  │→ │ Services │→ │ Mock Data  │  │ Database │ │
│  └─────────┘  └──────────┘  └────────────┘  └──────────┘ │
│                     ↓ (future)                               │
│              ┌──────────────┐                                │
│              │ Integrations │                                │
│              └──────────────┘                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   PostgreSQL         External APIs       Make.com
   (Railway)         (Gmail, GHL, etc.)  (Orchestration)
```

## Layer Responsibilities

### API Layer (`app/api/routes/`)

Thin HTTP handlers. Each route:
1. Receives the request
2. Injects dependencies (database session)
3. Delegates to a service class
4. Returns a Pydantic-validated response

No business logic lives in routes.

### Service Layer (`app/services/`)

Owns all business logic. Each domain has a dedicated service:

| Service | Domain |
|---------|--------|
| `OverviewService` | Executive dashboard, daily brief |
| `CalendarService` | Meetings and schedule |
| `InboxService` | Email classification and summaries |
| `CRMService` | Pipeline and deals |
| `ProjectService` | Initiatives and tasks |
| `ResearchService` | Business intelligence curation |
| `AssistantService` | AI chat and suggestions |
| `SettingsService` | User profile and integrations |

In v0.1, services return mock data from `mock_data.py`. In later versions, services will query the database and call integration modules.

### Data Layer

**PostgreSQL** stores persistent state: users, emails, meetings, deals, tasks, research items, and integration credentials.

**SQLAlchemy 2.0** provides the ORM with typed `Mapped` columns.

**Alembic** manages schema migrations.

### Integration Layer (`app/integrations/`) — Future

Each external service gets a dedicated integration module:

```
integrations/
├── gmail.py           # Gmail API — inbox sync, send
├── google_calendar.py # Google Calendar API — events
├── gohighlevel.py     # GoHighLevel API — CRM pipeline
├── openai.py          # OpenAI API — briefings, chat
├── clickup.py         # ClickUp API — projects/tasks
├── notion.py          # Notion API — knowledge base
└── make.py            # Make.com webhooks — orchestration
```

Integration modules expose a consistent internal interface. Services call integrations, never third-party APIs directly.

## How Future Integrations Fit

### Gmail (v0.3)

```
Gmail API → integrations/gmail.py → InboxService
```

- OAuth2 flow stores tokens in `Integration` model
- Periodic sync fetches new emails into `Email` table
- OpenAI classifies and summarizes emails into categories
- `InboxService.get_inbox()` queries `Email` instead of mock data

### Google Calendar (v0.2)

```
Google Calendar API → integrations/google_calendar.py → CalendarService
```

- OAuth2 stores calendar access tokens
- Sync imports events into `Meeting` table
- `CalendarService.get_calendar()` queries today's meetings from database
- Overview and Daily Brief services reuse the same meeting data

### GoHighLevel (v0.4)

```
GoHighLevel API → integrations/gohighlevel.py → CRMService
```

- API key stored in `Integration.config`
- Sync pulls deals/opportunities into `CRMDeal` table
- `CRMService.get_crm()` returns live pipeline data
- AI summaries generated via OpenAI integration

### OpenAI (v0.5)

```
OpenAI API → integrations/openai.py → OverviewService, AssistantService
```

- Powers executive summary generation in `DailyBrief`
- Generates AI recommendations on the overview dashboard
- Replaces mock chat responses in `AssistantService`
- Summarizes emails, deals, and research items

### Make.com (v0.6)

```
Make.com → Webhooks → Backend API → Services
```

- Orchestrates multi-step workflows (e.g. "new email → classify → notify → create CRM task")
- Triggers daily brief generation on schedule
- Connects integrations that don't have direct API access
- Backend exposes webhook endpoints for Make.com scenarios

### ClickUp (v0.6)

```
ClickUp API → integrations/clickup.py → ProjectService
```

- Syncs tasks and projects into `Task` table
- Progress and status pulled from ClickUp
- `ProjectService.get_projects()` returns live project data

## Authentication (Future)

v0.1 has no authentication. Planned approach:

- JWT-based auth with refresh tokens
- User model already includes `email` and `is_active`
- All service methods will accept `user_id` from the authenticated session
- Integration tokens scoped per user

## Deployment

| Component | Platform |
|-----------|----------|
| Frontend | Vercel / Netlify / Railway |
| Backend | Railway |
| Database | Railway PostgreSQL |
| Automations | Make.com (future) |

## Design Principles

1. **Thin routes, fat services** — business logic stays in services
2. **Integration isolation** — third-party APIs wrapped in dedicated modules
3. **Schema-first API** — Pydantic models define the contract with the frontend
4. **Progressive enhancement** — mock data → database → live integrations
5. **No over-engineering** — simple patterns that scale with the product
