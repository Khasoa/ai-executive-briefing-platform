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
│   ├── hooks/            # useApiQuery, useAsyncAction
│   ├── lib/              # cn, formatting, motion presets, signal vocabulary
│   ├── pages/            # One file per route
│   └── services/         # API client — every request the app makes
├── backend/              # FastAPI backend
├── docs/                 # Architecture, API and decision records
├── automation/           # n8n workflow definitions (future)
└── assets/               # Screenshots and demo assets
```

## Tech Stack

**Frontend** — React 19, JavaScript, Vite, Tailwind CSS v4, Framer Motion, React Router, shadcn-style primitives built on `class-variance-authority`.

**Backend** — Python, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL.

## Application Structure

| Route | Purpose |
|-------|---------|
| `/` | Executive dashboard: summary, KPIs, activity, today's focus |
| `/morning-brief` | The full briefing, formatted as a printable executive report |
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
# Optional demo data (idempotent): see backend/README.md
uvicorn app.main:app --reload --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs). Migrations: [docs/migrations.md](docs/migrations.md).

### Frontend

```bash
npm install
cp .env.example .env    # VITE_API_URL=http://localhost:8000
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

No page holds its own copy of server data — every view is rendered from an API response through `src/services/briefly.js`.

### Checks

```bash
npm run lint              # oxlint
npm run build             # production bundle
cd backend && pytest -q   # API contract and product invariants
```

The backend suite covers every endpoint, both mutation paths, and the invariants that define the product: no endpoint acts on the executive's behalf, and automatic actions cannot be enabled.

## Design Direction

A calm, spacious, premium SaaS surface in the spirit of Linear and Vercel: off-white page, white cards, deep emerald primary, warm amber accent, slate text. Subtle shadows, restrained glass, short transitions. No AI-blue gradients, no glow, no motion for its own sake.

The Morning Brief additionally uses a serif face for long-form passages and carries a print stylesheet so it can be presented or exported as-is.

## Future Integrations

Google Calendar, Gmail, Notion and GoHighLevel are wired through the same `IntegrationCard` and sync-history surface today, backed by curated data. OpenAI generates the brief, and n8n is reserved for scheduled generation. Adding a live provider means implementing one module in `backend/app/integrations/` — no schema or UI changes.

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [Roadmap](docs/roadmap.md)
- [Decisions](docs/decisions.md)
- [Backend README](backend/README.md)
