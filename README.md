# Briefly — AI Executive Briefing Platform

Briefly gives founders and executives one intelligent briefing every morning, assembled from the systems they already run on.

It is not a chatbot and not another productivity tool. Instead of opening Gmail, Google Calendar, a CRM and Notion separately, you open Briefly and immediately know what needs attention, which decisions are waiting, which meetings need preparation, which clients are at risk, and what to do first.

**The Morning Brief is the product.** Every other page exists to support it.

## Product Principles

1. Every feature answers one question: *what does the executive need to know right now?*
2. The AI summarises, prioritises, recommends, prepares and organises. It never decides.
3. Nothing is sent, moved or accepted without explicit human approval. Integration scopes are read-only.
4. Every statement is attributable — each recommendation names the system it came from.

## Repository Structure

```
ai-executive-partner/
├── src/                  # React frontend (Vite + JavaScript)
│   ├── components/
│   │   ├── cards/        # Reusable domain cards
│   │   ├── common/       # Page header, source chips, activity feed
│   │   ├── feedback/     # Loading, empty and error states
│   │   ├── layout/       # App shell and sidebar
│   │   └── ui/           # shadcn-style primitives
│   ├── hooks/            # useApiQuery, useAsyncAction, useToast
│   ├── lib/              # cn, formatting, motion presets, signal vocabulary
│   ├── pages/            # One file per route
│   └── api/              # HTTP client + one module per backend domain
├── backend/              # FastAPI backend
├── docs/                 # Architecture, API and decision records
├── automation/           # n8n orchestration docs / workflow notes
└── assets/               # Screenshots and demo assets
```

## Tech Stack

**Frontend** — React 19, JavaScript, Vite, Tailwind CSS v4, Framer Motion, React Router, shadcn-style primitives built on `class-variance-authority`.

**Backend** — Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL.

## Quality Engineering & Testing

Briefly uses automated tests to validate backend/API behaviour, frontend behaviour, mocked provider integrations and sync, authentication/OAuth, data integrity, edge cases (including timezone boundaries), and product invariants such as “recommend, never act.”

**Tools:** pytest + FastAPI TestClient on the backend; Vitest, Testing Library, and jsdom on the frontend.

**Suite size (current):** 295 automated tests (241 backend, 54 frontend). Run locally with `cd backend && pytest -q` and `npm run test`.

High-value examples:
- **OAuth / user isolation** — connecting one provider must not mark unrelated providers connected (backend + UI).
- **Sync / deletion reconciliation** — ClickUp and monday.com syncs archive tasks missing from a complete remote list even when an incremental watermark exists, and skip mass-archive when pagination is incomplete (prevents stale Overview tasks).
- **Meeting / timezone edges** — prep and “today” windows respect user timezone and midnight boundaries.
- **Product invariants** — OpenAPI paths must not expose act-on-behalf verbs; automatic action approval cannot be enabled.
- **Overview consistency** — the same work item cannot appear twice across Actions and Focus urgency buckets.

## Application Structure

| Route | Purpose |
|-------|---------|
| `/` | Executive dashboard: summary, KPIs, activity, today's focus |
| `/morning-brief` | The full briefing, formatted as a printable executive report |
| `/weekly-digest` | Weekly email memory + next-week planning |
| `/inbox` | Intelligent email summaries, not a raw message list |
| `/meetings` | Meeting intelligence: context, talking points, questions, risks |
| `/crm` | Only the opportunities that need executive attention |
| `/ask` | Executive intelligence workspace — cited reports, not chat |
| `/integrations` | Connection status, sync history, configuration |
| `/settings` | Profile, preferences, notifications, security, theme, accounts |

## Reusable Components

The pages are thin. Almost everything on screen is one of these cards:

`ExecutiveSummaryCard` · `MorningBriefCard` · `MeetingCard` · `EmailCard` · `DealCard` · `KPIWidget` · `RecommendationCard` · `IntegrationCard` · `ReportCard`

Urgency, severity and priority all share one vocabulary in `src/lib/signals.js`, so a "critical" item looks identical whether it is an email, a risk or a deal.

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Configure DATABASE_URL, then:
alembic upgrade head
python3 scripts/seed.py   # optional, idempotent demo data
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs). Migrations: [docs/migrations.md](docs/migrations.md). Backend onboarding: [backend/README.md](backend/README.md).

### Frontend

```bash
npm install
cp .env.example .env    # VITE_API_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Unauthenticated visitors land on `/login`. For Google, Notion, or GoHighLevel OAuth in the browser, set backend `OAUTH_SUCCESS_REDIRECT=http://localhost:5173/oauth/callback`.

No page holds its own copy of server data — every view is rendered from an API response through `src/api/` (one module per backend domain). Session tokens live in `localStorage` and are attached as `Authorization: Bearer`.

### Checks

```bash
npm run lint              # ESLint
npm run test              # Vitest (auth + client)
npm run build             # production bundle
cd backend && pytest -q   # backend API, sync, OAuth, and product invariants
```

Frontend lint uses **ESLint** (`eslint.config.js`) with `eslint-plugin-react`, React Hooks, and React Refresh for the Vite + JavaScript app.

See [Quality Engineering & Testing](#quality-engineering--testing) for suite scope and examples. Notable invariants include: no endpoint acts on the executive's behalf, and automatic actions cannot be enabled.

## Deployment

Briefly uses a split production deployment:

- **Frontend** — React/Vite deployed on Vercel
- **Backend** — FastAPI deployed on Railway
- **Database** — PostgreSQL hosted on Railway
- **Automation** — n8n handles scheduled synchronization and briefing workflows

Production URLs:

- Frontend: `https://ai-executive-briefing-platform.vercel.app`
- Backend: `https://briefly-production-5b08.up.railway.app`

The frontend communicates with the deployed backend through `VITE_API_URL`. Production OAuth callbacks and CORS origins must use the deployed frontend/backend URLs rather than localhost values.

No additional environment variables or database migrations are required for the current integration metrics, task reconciliation, or meeting-intelligence fixes.

## Design Direction

A calm, spacious, premium SaaS surface in the spirit of Linear and Vercel: off-white page, white cards, deep emerald primary, warm amber accent, slate text. Subtle shadows, short transitions. No AI-blue gradients, no glow, no motion for its own sake.

The Morning Brief additionally uses a serif face for long-form passages and carries a print stylesheet so it can be presented or exported as-is.

## Integrations

Google Calendar and Gmail sync into `Meeting` / `Email` when connected. Notion syncs into `NotionItem` (`NOTION_CLIENT_*`). GoHighLevel syncs opportunities into `Opportunity` (`GHL_CLIENT_*`). monday.com and ClickUp sync tasks into provider-neutral `WorkItem` rows (`MONDAY_CLIENT_*`, `CLICKUP_CLIENT_*`). OpenAI powers Morning Brief, Weekly Digest, meeting prep, email summaries, and Ask (`OPENAI_API_KEY`). Without those keys, the API keeps curated/`demo_data` behaviour. n8n schedules sync + brief regeneration via secret-authenticated webhooks (`N8N_WEBHOOK_SECRET`) — see [automation/n8n-daily-brief.md](automation/n8n-daily-brief.md).

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Roadmap](docs/roadmap.md)
- [Decisions](docs/decisions.md)
- [Backend README](backend/README.md)
