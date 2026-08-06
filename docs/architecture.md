# Briefly Architecture

## Overview

Briefly reads an executive's connected systems and produces one thing: the Morning Brief. Every other surface — Overview, Inbox, Meetings, CRM, Ask Briefly — is a different view onto the same underlying intelligence.

The system is a modular monolith: one React frontend, one FastAPI backend with clear internal boundaries, one database.

```
┌──────────────────────────────────────────────────────────────┐
│                  React Frontend (Vite + JS)                  │
│  Overview · Morning Brief · Inbox · Meetings · CRM ·         │
│  Ask Briefly · Integrations · Settings                       │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST (JSON, camelCase)
┌───────────────────────────▼──────────────────────────────────┐
│                       FastAPI Backend                        │
│   Routes ──▶ Services ──▶ PostgreSQL (+ demo_data fallback)  │
│                   │                                          │
│                   └──▶ Integrations (future, read-only)      │
└───────────────────────────┬──────────────────────────────────┘
                            │
       ┌────────────────────┼─────────────────────┐
       ▼                    ▼                     ▼
  PostgreSQL         Google · Notion ·          OpenAI
                     GoHighLevel                (generation)
                            ▲
                            └── n8n (scheduled generation)
```

## Frontend

### Layer responsibilities

| Layer | Responsibility |
|-------|---------------|
| `services/client.js` | One `fetch` wrapper: base URL, JSON, abort signals, `ApiError` |
| `services/briefly.js` | One named function per endpoint. Nothing else builds a URL |
| `hooks/useApiQuery.js` | Fetch, loading, error, refetch and abort for a page |
| `hooks/useAsyncAction.js` | One-off mutations with pending and error state |
| `pages/` | Compose cards from an API response. No data of their own |
| `components/cards/` | Domain cards — the actual product surface |
| `components/ui/` | Unstyled-by-domain primitives (button, card, badge, tabs…) |
| `lib/signals.js` | Shared urgency vocabulary so severity looks the same everywhere |

### Tooling

The frontend is plain JavaScript on Vite. Lint with ESLint (`npm run lint`, config in `eslint.config.js`) using `eslint-plugin-react`, React Hooks, and React Refresh. There is no TypeScript and no Prettier in this repository.

### Why pages hold no data

Each page calls exactly one `useApiQuery`, then renders. Mutations (`regenerate`, checklist toggle, integration sync, preference change) return the updated object and the page applies it with `setData`. There is no client-side duplicate of server state to fall out of sync.

The application shell fetches `/workspace` once for identity, brief freshness and navigation counts, so no page re-fetches the user.

### Design system

Tokens live in `src/index.css` under Tailwind v4's `@theme`. Off-white background, white cards, deep emerald primary, warm amber accent, slate text, tight radii and low-contrast borders. Motion is limited to short opacity/translate entrances and one accordion.

The Morning Brief adds a serif face for long-form passages and a print stylesheet, because it is meant to be read, presented or exported rather than scanned.

## Backend

### Layer responsibilities

**Routes** (`app/api/routes/`) are thin: receive, inject the session, delegate, return a validated response. No business logic.

**Services** (`app/services/`) own everything else:

| Service | Owns |
|---------|------|
| `WorkspaceService` | Shell payload; badges via Inbox/Meeting/CRM; brief meta via MorningBrief |
| `OverviewService` | Dashboard; DailyBrief summary slice; brief meta via MorningBrief |
| `DailyBriefService` | `daily_briefs` |
| `MorningBriefService` | `morning_briefs`, `brief_actions` |
| `InboxService` | `emails` |
| `MeetingService` | `meetings` |
| `CRMService` | `opportunities` |
| `AskService` | Cited reports (curated until OpenAI); sources via IntegrationService |
| `IntegrationService` | `integrations`, `sync_events` |
| `SettingsService` | Preferences UI state (curated until auth) |

Persistence-backed services read PostgreSQL first and fall back to `demo_data.py` when a table is empty or unreachable (`db_fallback.py`). Cross-domain reads never bypass the owning service. Migration history: [migrations.md](./migrations.md).

**Schemas** (`app/schemas/`) define the API contract only — separate from ORM models. `common.py` holds the shared vocabulary — urgency, severity, confidence, sources and citations.

**Models** (`app/models/`) are persistence-only: `User`, `MorningBrief`, `BriefAction`, `Meeting`, `Email`, `Opportunity`, `Integration`, `SyncEvent`, `DailyBrief`.

### Read-only by design

No endpoint sends an email, moves a deal or accepts a meeting. `POST /ask` can produce a draft; only the executive can act on it. `autoApproveActions` exists in settings purely to be permanently disabled, making the guarantee visible in the product.

## How the integrations fit

Each provider becomes one module in `app/integrations/` exposing a consistent internal interface. Services call integrations; they never touch a third-party SDK directly.

```
integrations/
├── gmail.py             → InboxService, MorningBriefService
├── google_calendar.py   → MeetingService
├── gohighlevel.py       → CRMService
├── notion.py            → OverviewService, MorningBriefService
├── openai.py            → MorningBriefService, AskService
└── n8n.py               → scheduled generation webhooks
```

**Gmail** — OAuth2 tokens on `Integration.config`; sync writes into `Email`; OpenAI fills `ai_summary`, `priority` and `suggested_response`. `InboxService` swaps its source and nothing else changes.

**Google Calendar** — events sync into `Meeting`; the generated preparation (`intelligence` JSONB) is produced once per event and reused by both the Meetings page and the brief.

**GoHighLevel** — opportunities sync into `Opportunity`; `risk_level` is derived from engagement recency, stage movement and signals found in linked threads.

**Notion** — indexed pages provide the internal context (plans, metrics) that lets the brief name team blockers.

**OpenAI** — turns the synced corpus into `MorningBrief.sections` and answers Ask Briefly questions. Citations come from which records were retrieved, not from the model.

**n8n** — calls `POST /morning-brief/regenerate` on a schedule so the brief is ready before the executive wakes up.

## Data flow: generating a brief

```
06:25  n8n triggers generation
06:26  Integrations sync → Email, Meeting, Opportunity rows updated
06:28  MorningBriefService retrieves today's records per domain
06:29  OpenAI produces summary, priorities, risks, focus, delegation
06:30  MorningBrief + BriefAction rows written, SyncEvent logged
06:31  GET /morning-brief serves it; the shell shows "generated 2 minutes ago"
```

## Deployment

| Component | Platform |
|-----------|----------|
| Frontend | Vercel / Netlify / Railway |
| Backend | Railway |
| Database | Railway PostgreSQL |
| Scheduling | n8n |

## Principles

1. **One output.** Features earn their place by improving the brief.
2. **Thin routes, fat services.** Business logic is testable without HTTP.
3. **Schema-first.** Pydantic defines the contract; the frontend never guesses.
4. **Attribution everywhere.** If the AI says it, the API names the source.
5. **Human-in-the-loop.** Read scopes only, drafts never sent.
6. **Progressive enhancement.** Curated data → database → live integrations, without structural change.
