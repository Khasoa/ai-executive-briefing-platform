# Briefly Architecture

## Overview

Briefly reads an executive's connected systems and produces one thing: the Morning Brief. Every other surface — Overview, Inbox, Meetings, CRM, Ask Briefly — is a different view onto the same underlying intelligence.

The system is a modular monolith: one React frontend, one FastAPI backend with clear internal boundaries, one database.

```
┌──────────────────────────────────────────────────────────────┐
│                  React Frontend (Vite + JS)                  │
│  Overview · Morning Brief · Weekly Digest · Inbox ·          │
│  Meetings · CRM · Ask Briefly · Integrations · Settings       │
└───────────────────────────┬──────────────────────────────────┘
                            │ REST (JSON, camelCase)
┌───────────────────────────▼──────────────────────────────────┐
│                       FastAPI Backend                        │
│   Routes ──▶ get_current_user ──▶ Services (scoped by user)  │
│                   │                                          │
│                   ├──▶ PostgreSQL (+ demo_data for demo user)│
│                   └──▶ Integrations (Google, Notion, GHL,      │
│                        monday, ClickUp, OpenAI)              │
└───────────────────────────┬──────────────────────────────────┘
                            │
       ┌────────────────────┼─────────────────────┐
       ▼                    ▼                     ▼
  PostgreSQL         Synced provider corpus     OpenAI
                     (Calendar/Gmail/Notion/    (via AIService)
                      GHL/monday/ClickUp)
                            ▲
                            └── n8n (orchestration only)
```

## Frontend

### Layer responsibilities

| Layer | Responsibility |
|-------|---------------|
| `api/client.js` | One `fetch` wrapper: base URL, JSON, timeout, abort, `ApiError` |
| `api/*.js` | One module per backend domain; nothing else builds a URL |
| `hooks/useApiQuery.js` | Fetch, soft refresh, classified errors, abort for a page |
| `hooks/useAsyncAction.js` | One-off mutations with pending and `{ data, error }` result |
| `hooks/useToast.js` | Shared success/error toasts for mutations |
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

**Routes** (`app/api/routes/`) are thin: receive, inject the session and current user, delegate, return a validated response. No business logic.

**Auth** (`app/api/deps.py`, `app/services/auth_service.py`, `app/services/oauth_service.py`, `app/core/security.py`, `app/integrations/oauth/`):
- JWT access tokens + opaque, hashed, rotating refresh tokens
- Google Authorization Code Flow via `OAuthProvider` (encrypted tokens on `Integration`)
- `get_current_user` resolves Bearer → `User`, or demo user when `AUTH_REQUIRED=false`
- Domain services take `(db, user)` and filter ownership by `user_id`

**Services** (`app/services/`) own everything else:

| Service | Owns |
|---------|------|
| `AuthService` | Register, login, refresh, logout, access-token resolution |
| `WorkspaceService` | Shell payload; badges via Inbox/Meeting/CRM; brief meta via MorningBrief |
| `OverviewService` | Dashboard; DailyBrief summary slice; brief meta via MorningBrief |
| `DailyBriefService` | `daily_briefs` (per user) |
| `MorningBriefService` | `morning_briefs`, `brief_actions` (AI + curated failover) |
| `InboxService` | `emails` (lazy AI summary on detail) |
| `MeetingService` | `meetings` (lazy AI prep on detail) |
| `CRMService` | `opportunities` |
| `AskService` | Cited reports via `AIService`; history in `ask_reports` |
| `AIService` | Sole OpenAI orchestration; returns `None` → curated failover |
| `IntegrationService` | Canonical catalog ∪ user `integrations` / `sync_events` |
| `SettingsService` | Profile from `User`; preferences on demo via curated state, else `User.preferences` |

Persistence-backed services read PostgreSQL first and fall back to `demo_data.py` when a table is empty or unreachable *for the demo user* (`db_fallback.py` + `is_demo_user`). Non-demo users get empty collections instead. Cross-domain reads never bypass the owning service. Migration history: [migrations.md](./migrations.md).

**Schemas** (`app/schemas/`) define the API contract only — separate from ORM models. `common.py` holds the shared vocabulary — urgency, severity, confidence, sources and citations.

**Models** (`app/models/`) are persistence-only: `User`, `RefreshToken`, `OAuthState`, `OAuthLoginTicket`, `MorningBrief`, `BriefAction`, `Meeting`, `Email`, `Opportunity`, `Integration`, `SyncEvent`, `DailyBrief`, `AskReport`.

### Read-only by design

No endpoint sends an email, moves a deal or accepts a meeting. `POST /ask` can produce a draft; only the executive can act on it. `autoApproveActions` exists in settings purely to be permanently disabled, making the guarantee visible in the product.

## How the integrations fit

Each provider becomes one module in `app/integrations/` exposing a consistent internal interface. Services call integrations; they never touch a third-party SDK directly.

```
integrations/
├── oauth/
│   ├── base.py          → OAuthProvider interface
│   ├── google.py        → Google identity + calendar/gmail scopes
│   ├── notion.py        → Notion workspace bot OAuth
│   ├── gohighlevel.py   → GHL Marketplace Location OAuth
│   ├── monday.py        → monday.com OAuth
│   └── clickup.py       → ClickUp OAuth
├── google_calendar.py   → CalendarSyncService (events → Meeting)
├── gmail.py             → GmailSyncService (messages → Email)
├── notion.py            → NotionClient (search / databases / blocks)
├── openai.py            → OpenAIClient (Responses API); used only by AIService
├── gohighlevel.py       → GHLClient (opportunities / pipelines)
├── monday.py            → MondayClient (boards / items GraphQL)
└── clickup.py           → ClickUpClient (teams / tasks REST)
```

n8n does not live under `integrations/` — it calls `POST /webhooks/n8n/*` → `OrchestrationService`.

### Notion dependency graph

```
Routes (thin)
  └─▶ IntegrationService.trigger_sync("notion")
        └─▶ NotionSyncService
              └─▶ OAuthService (encrypted Integration tokens)
              └─▶ NotionClient (integrations/notion.py)
                    └─▶ NotionItem rows (idempotent upsert)
  └─▶ OverviewService / AIService
        └─▶ NotionService (read-only queries)
```

Never call Notion from a route. Disconnected Notion → identical Overview / Brief / Ask behaviour as before (demo_data for the demo tenant; empty for others).

### GoHighLevel dependency graph

```
Routes (thin)
  └─▶ IntegrationService.trigger_sync("gohighlevel")
        └─▶ GHLSyncService
              └─▶ OAuthService (encrypted Integration tokens)
              └─▶ GHLClient (integrations/gohighlevel.py)
                    └─▶ Opportunity rows (external_id=ghl:…)
  └─▶ CRMService / AIService
        └─▶ crm_intelligence.derive_crm_signals (read-only)
```

Disconnected GHL → CRM keeps curated/`demo_data` or user-local opportunities; no fabricated pipeline.

### n8n orchestration

```
n8n Schedule
  └─▶ POST /webhooks/n8n/daily|weekly|run  (X-Briefly-N8N-Secret)
        └─▶ OrchestrationService
              └─▶ per-provider sync (isolated failures)
              └─▶ MorningBriefService / WeeklyDigestService
```

n8n never owns CRM/email/calendar logic. FastAPI remains the system of record.

### AI dependency graph

```
Routes (thin)
  └─▶ Domain services (MorningBrief / Meeting / Inbox / Ask)
        └─▶ AIService  (prompts in ai_prompts.py, failover, normalisation)
              └─▶ context: Meetings, Emails, CRM, Morning Brief, Notion,
                  Settings, Integrations
              └─▶ OpenAIClient (integrations/openai.py → Responses API)
        └─▶ curated demo_data  ◀── on any OpenAI failure / missing key
```

**Provider flow:** gather read-only context from owning services → structured JSON schema prompt → parse/validate → persist. Never call OpenAI from a route.

**Failover:** missing `OPENAI_API_KEY`, timeout, 429, 5xx/auth failure, or malformed JSON → `AIService` returns `None` → caller uses today's curated path. Demo mode unchanged.

**Cache strategy:**
- Morning Brief: today's `MorningBrief` row; regenerate forces a new OpenAI call
- Weekly Digest: `weekly_digests` row per `(user_id, week_start)` for the rolling 7-day window; regenerate forces a new call
- Meeting prep: non-empty `Meeting.intelligence` (or `manuallyEdited`) skips AI
- Email AI: non-empty `ai_summary` + `suggested_response` skips AI
- Ask: each answer persisted to `ask_reports`; no answer cache (questions vary)

**Google OAuth** — Authorization Code Flow stores encrypted access/refresh tokens on `Integration(provider=google)` with `openid email profile calendar.readonly gmail.readonly`. That `google` row is the sole credential store.

**Google Calendar / Gmail cards** — Integrations UI catalog ids `google-calendar` and `gmail` project connection state from the user’s `provider=google` row (and optional mirror rows written by sync for audit). Sync always refreshes tokens via `provider=google` and writes `Meeting` / `Email` rows for the **authenticated** `user_id`. A connected Integration on the demo user is never shown to a different Google-authenticated user.

**OAuth state** — `oauth_states` rows are created on `/auth/oauth/{provider}/start` (same `DATABASE_URL` as callback), TTL `OAUTH_STATE_EXPIRE_MINUTES` (default 10), timezone-aware UTC expiry, single-use `consumed_at`. A new start invalidates prior unused states for the same provider + initiator so stale Google tabs cannot complete. Callback and start must hit the same backend process/database.

**Google Calendar** — `CalendarSyncService` incrementally syncs primary calendar events into `Meeting`. Local prep/intelligence preserved on update.

**Gmail** — `GmailSyncService` syncs messages into `Email`, leaving `ai_summary` / `suggested_response` empty for `InboxService` → `AIService`.

**Notion** — `NotionOAuthProvider` + long-lived bot token on `Integration(provider=notion)`. `NotionSyncService` incrementally syncs pages/databases into `NotionItem` (watermark on `last_edited_time`, selected databases, preserves `intelligence`). `NotionService` feeds Morning Brief / Ask context and Overview tasks/docs/projects.

**OpenAI** — `AIService` turns the synced corpus into Morning Brief sections, Weekly Email Digests, meeting intelligence, email summaries, and Ask reports. Prompts/schemas live in `ai_prompts.py`.

**Weekly Digest** — `WeeklyDigestService` builds cross-system context from user-scoped `Email`, `Meeting`, `Opportunity`, `NotionItem`, and `WorkItem` rows (only sources with data), then caches memory + Next Week Outlook in `weekly_digests`. Curated fallback when AI is off or signals are thin. Never uses demo curated content for authenticated non-demo users. Does not replace the Morning Brief.

**GoHighLevel** — `GoHighLevelOAuthProvider` + Location token on `Integration(provider=gohighlevel)`. `GHLSyncService` upserts opportunities (`external_id`), preserves AI/risk fields, closes missing open deals. `crm_intelligence` feeds AI context with source attribution.

**monday.com / ClickUp** — OAuth → sync into `WorkItem` (`external_id` prefixed). `WorkItemService` feeds Overview (when Notion is idle) and AI context (`workItems`: overdue, due soon, high priority, blocked, completed, ownership). Independently optional.

**n8n** — secret-authenticated webhooks only. Recommended daily: sync Calendar → Gmail → Notion → GHL → monday → ClickUp → regenerate Morning Brief. Weekly: sync + Weekly Digest. Per-step failure isolation.

## Data flow: generating a brief

```
06:25  n8n POST /webhooks/n8n/daily (or GET /morning-brief on cache miss)
06:26  Integrations sync → Email, Meeting, NotionItem, Opportunity rows updated
06:28  AIService gathers context via Meeting/Inbox/CRM/Notion/Integration/Settings
06:29  OpenAI Responses API returns structured JSON (or curated failover)
06:30  MorningBrief + BriefAction rows written
06:31  GET /morning-brief serves the cached row until regenerate
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
