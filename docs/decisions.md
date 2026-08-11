# Architectural Decisions

Key decisions behind Briefly and the reasoning for each.

---

## ADR-001: The Morning Brief is the product

**Decision:** One page is the output; every other page supports it.

**Why:**
- An executive tool that does eight things well is still eight things to check every morning
- A single artefact can be read in five minutes, printed, or forwarded to a chief of staff
- It gives every feature a test: does this make tomorrow's brief better?

**Consequence:** Pages that did not serve the brief — Projects, Research, Calendar grid, generic AI chat — were removed rather than redesigned.

---

## ADR-002: Recommend, never act

**Decision:** No endpoint sends email, moves a deal or accepts a meeting. Integration scopes are read-only.

**Why:**
- Trust is the binding constraint for an AI product with access to a founder's inbox and pipeline
- A wrong summary costs a minute; a wrong send costs a relationship
- Draft-and-approve is a useful workflow on its own

**How it shows up:** `suggestedResponse` on every email, a "Draft — not sent" label on generated text, and `autoApproveActions` in settings that exists only to be permanently disabled.

---

## ADR-003: Cite every AI statement

**Decision:** Recommendations, risks and Ask Briefly reports name the systems they came from.

**Why:**
- An executive cannot act on a claim they cannot verify
- Citations expose the failure mode where the model is confident about a system it never read
- Once generation is retrieval-backed, citations fall out of which records were retrieved

**Implementation:** `Source` and `CitationSchema` in `schemas/common.py`; `SourceChip` renders them identically everywhere.

---

## ADR-004: One urgency vocabulary

**Decision:** `critical`, `high`, `medium`, `low` across every domain — email priority, risk severity, deal risk, recommendation priority.

**Why:**
- Three different colour schemes for "urgent" teaches the reader nothing and slows scanning
- Lists can be sorted by consequence with one shared comparator
- The API enforces it via a shared `Literal`, so the UI never encounters an unmapped value

**Implementation:** `schemas/common.py` on the backend, `lib/signals.js` on the frontend.

---

## ADR-005: JavaScript, not TypeScript

**Decision:** The frontend is plain JavaScript with JSX.

**Why:**
- Explicitly specified for this product
- Pydantic already defines and validates the API contract at the boundary that matters
- `jsconfig.json` preserves path aliases and editor intelligence

**Trade-off:** No compile-time guarantee that a component matches an API response. Mitigated by keeping every fetch in `src/api/` and rendering directly from responses, and by a smoke test that mounts each page against the live API.

---

## ADR-006: Pages hold no local copy of server data

**Decision:** Each page runs one `useApiQuery`. Mutations return the updated object and the page applies it via `setData`.

**Why:**
- Two copies of the truth drift; one does not
- Optimistic local state would have to replicate server rules (checklist progress, pipeline weighting)
- Keeps pages small enough to read in one screen

---

## ADR-007: Thin routes, fat services

**Decision:** Routes receive, inject the session, delegate and return. All logic lives in service classes.

**Why:**
- Services are testable without HTTP
- Swapping curated data for a database query or an integration touches one class
- Each domain has one obvious owner

```python
@router.get("", response_model=CRMResponse)
def get_pipeline(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CRMResponse:
    return CRMService(db, user).get_pipeline()
```

---

## ADR-008: Demo data behind real service boundaries

**Decision:** Persistence-backed services read PostgreSQL first and fall back to `demo_data.py` only when a table is empty or unreachable *and* the request is the demo user. Surfaces that are not yet persisted (Ask curated reports, Settings notifications/theme, Overview KPIs/activity/focus) still read `demo_data` through their owning service for the demo tenant. Authenticated non-demo users see empty lists instead of Lydia's curated portfolio data.

**Why:**
- The frontend can be built and demonstrated end to end immediately
- Response shapes stay stable while integrations and OpenAI are wired in
- Empty-table / DB-error fallbacks degrade a page instead of breaking it
- Computed values (weighted pipeline, prep counts, scheduled minutes) are calculated, not hardcoded
- Multi-user isolation must never leak curated demo content into a real account

**Trade-off:** Fallback and still-curated surfaces reset on process restart when the database is empty. Acceptable until those domains are fully persisted and externally sourced.

---

## ADR-009: Schemas separate from ORM models

**Decision:** `app/schemas/` defines the API contract; `app/models/` defines storage.

**Why:**
- The frontend wants camelCase and flattened, composed objects; the database wants snake_case and normalised rows
- A response often spans several tables (a brief pulls from meetings, emails and opportunities)
- Prevents internal columns from leaking into the API

---

## ADR-010: Integration modules, never direct SDK calls

**Decision:** Each provider gets a module in `app/integrations/` exposing a consistent internal interface.

**Why:**
- A Gmail API change touches one file
- Integrations can be stubbed in tests
- Services stay readable — they express business rules, not HTTP plumbing

---

## ADR-011: Tailwind v4 theme tokens over a config file

**Decision:** Design tokens are CSS custom properties in `@theme` inside `src/index.css`.

**Why:**
- Tailwind v4's native approach; no `tailwind.config.js` to keep in sync
- Tokens are inspectable in the browser and reusable in plain CSS (print styles, scrollbars)
- Renaming a colour is one edit, and every utility follows

---

## ADR-012: The brief is a document, not a dashboard

**Decision:** The Morning Brief uses numbered sections, a serif face for prose, and a print stylesheet.

**Why:**
- Executives read reports; they scan dashboards. The brief is meant to be read
- Printing and presenting are real behaviours for a document that summarises a business day
- Visual separation from the rest of the app signals that this page is the output

---

## ADR-013: Flat routes, no `/api` prefix

**Decision:** `/overview`, `/inbox`, `/morning-brief` at the root; health at `/health`.

**Why:**
- Frontend and backend deploy separately, so there is no path collision to avoid
- Simpler client code
- A `/v1` prefix can be added when there is a second version to serve

---

## ADR-014: Configuration through pydantic-settings

**Decision:** All configuration loads from environment variables into a cached `Settings` object.

**Why:**
- Railway injects configuration as environment variables
- Type-safe with sensible defaults for local development
- One source of truth for database URL, CORS origins and log level

---

## ADR-015: Auth foundation with demo fallback

**Decision:** Password + JWT access tokens + opaque rotating refresh tokens, with `AUTH_REQUIRED=false` resolving missing Bearer credentials to the demo user (`lydia@arcadiasystems.com`).

**Why:**
- Portfolio demos must keep working without a login screen
- Future Google OAuth needs a stable `User` row and the same `get_current_user` dependency
- Refresh tokens must be revocable on logout (opaque hash in PostgreSQL), while access tokens stay short-lived JWTs
- `hashed_password` is nullable so OAuth-only accounts can exist later without inventing a password

**How it shows up:**
- `POST /auth/register|login|refresh|logout`, `GET /auth/me`
- Every domain route injects `User` via `get_current_user` and filters by `user_id`
- Curated `demo_data` fallbacks apply only when `is_demo_user(user)` is true
- Flip `AUTH_REQUIRED=true` to require a Bearer token on protected routes

**Google OAuth later:** exchange the Google code → find-or-create `User` by email (or link table) → issue the same `TokenResponse`. Calendar/Gmail scopes land on `Integration` rows owned by that user.

---

## ADR-016: OAuth providers behind a shared abstraction

**Decision:** Authorization Code Flow is implemented once as `OAuthProvider` (`app/integrations/oauth/`). Google is the first concrete provider. Provider tokens are Fernet-encrypted inside `integrations.config`; CSRF state and frontend login tickets are first-class tables.

**Why:**
- Microsoft / Notion / GoHighLevel can register the same interface without touching auth routes
- Encrypted-at-rest tokens keep secrets out of plaintext JSONB dumps
- Briefly JWT issuance stays in `AuthService.issue_tokens` so password and OAuth share one session model
- Auth-only Google scopes (`openid email profile`) keep Calendar/Gmail sync out of this phase

**How it shows up:**
- `GET /auth/oauth/{provider}/start|callback`, ticket exchange, status, provider refresh, disconnect
- `Integration(provider="google")` stores encrypted oauth + profile metadata for later sync modules
- Unconfigured Google credentials → `503` on start; demo mode unchanged

---

## ADR-017: Calendar sync writes Meetings; MeetingService stays read-only

**Decision:** `CalendarSyncService` owns Google → `Meeting` persistence. `MeetingService` continues to read `meetings` with demo fallback. Sync is incremental (`syncToken`), idempotent (`external_id`), preserves local prep/intelligence, and is webhook-ready via `POST /webhooks/google/calendar`.

**Why:**
- Avoids redesigning the Meetings API contract
- Demo mode keeps working when no synced rows exist
- Push notifications and manual `POST /integrations/google-calendar/sync` share one apply path
- Cancelled Google events delete the matching Meeting so the UI never shows ghosts

**How it shows up:**
- Tokens from `Integration(provider=google)`; sync cursor / channel on `config.calendar`
- UI row `google-calendar` mirrored for status + sync history
- Partial unique index `uq_meetings_user_external`

---

## ADR-018: Gmail sync writes Emails; InboxService stays read-only

**Decision:** `GmailSyncService` owns Gmail → `Email` persistence. `InboxService` continues to read `emails` with demo fallback. Sync is incremental (`historyId`), idempotent (`external_id=gmail:{messageId}`), stores provider labels, and does not call AI.

**Why:**
- Avoids redesigning the Inbox API contract
- Demo mode keeps working when no synced rows exist
- Labels and message ids come from Gmail; local AI fields stay empty until a later phase
- Pub/Sub webhook and manual `POST /integrations/gmail/sync` share one apply path

**How it shows up:**
- Tokens from `Integration(provider=google)`; cursor on `config.gmail.history_id`
- UI row `gmail` mirrored for status + sync history
- Partial unique index `uq_emails_user_external`
- `ai_summary` / `suggested_response` left empty at sync time for `AIService` fill

---

## ADR-019: OpenAI only through AIService, with curated failover

**Decision:** All generation goes `DomainService → AIService → OpenAIClient` (Responses API). `AIService` returns `None` on missing key, timeout, rate limit, unavailability, or malformed JSON so callers keep today's curated/`demo_data` paths. Prompts and JSON schemas live in `ai_prompts.py`. Ask history is persisted in `ask_reports` (migration `008`).

**Why:**
- One place owns provider errors, schema validation, and prompt construction
- Demo mode and API contracts stay stable without an API key
- Caching is explicit (Morning Brief row; non-empty meeting/email AI fields)
- Manual edits are never overwritten

**How it shows up:**
- Env: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBED_MODEL`, `OPENAI_TIMEOUT_SECONDS`
- Morning Brief cache = today's row; `POST /morning-brief/regenerate` forces refresh
- `Meeting.intelligence` / email AI fields filled lazily on detail reads when empty
- `AskService` persists every answer; curated reports remain the failover

---

## ADR-020: Notion through OAuthService + NotionSyncService

**Decision:** Notion uses the same `OAuthProvider` registry as Google. Long-lived workspace bot tokens are Fernet-encrypted on `Integration(provider=notion)`. `NotionSyncService` owns all Notion API I/O via `NotionClient`; routes stay thin. Synced pages land in `notion_items` (migration `009`) with idempotent `(user_id, external_id)` upserts. AI-generated `intelligence` is never overwritten. Incremental sync uses a `last_edited_watermark` in `integrations.config.notion`, plus optional `selected_database_ids`.

**Why:**
- Reuses encrypted token storage and CSRF/ticket OAuth machinery
- Notion tokens do not refresh — `OAuthService.refresh_provider_access_token` treats `expires_at=None` as valid
- Workspace installs must link to an existing Briefly session (synthetic `@users.notion.local` emails do not create users)
- Disconnected Notion leaves Overview / Morning Brief / Ask contracts unchanged

**How it shows up:**
- Env: `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, `NOTION_REDIRECT_URI`
- `POST /integrations/notion/sync` → `NotionSyncService`
- `AIService` context includes outstanding tasks, deadlines, projects, decisions, blocked work
- Overview surfaces today's tasks, overdue work, recent docs, and project status when Notion items exist

---

## ADR-021: GoHighLevel through OAuthService + GHLSyncService

**Decision:** GoHighLevel uses the shared `OAuthProvider` registry (Marketplace Location Authorization Code Flow). Access/refresh tokens are Fernet-encrypted on `Integration(provider=gohighlevel)`. `GHLSyncService` owns all GHL API I/O via `GHLClient`; routes stay thin. Opportunities upsert into the existing `Opportunity` model with `external_id=ghl:{id}` (migration `011` partial unique index). Local `ai_summary`, `recommended_action`, `risk_level`, and `signals` are never overwritten when already set. Closed/missing open deals are marked closed rather than hard-deleted.

**Why:**
- Reuses encrypted token storage and CSRF/ticket OAuth machinery
- Avoids a parallel CRM concept — CRMService / AIService stay the readers
- AI is not the source of truth for pipeline state; `crm_intelligence` only derives signals from synced fields
- Disconnected GHL leaves CRM contracts and demo behaviour unchanged

**How it shows up:**
- Env: `GHL_CLIENT_ID`, `GHL_CLIENT_SECRET`, `GHL_REDIRECT_URI`
- `POST /integrations/gohighlevel/sync` → `GHLSyncService`
- Connect while signed in (refuse `@users.gohighlevel.local` auto-provision)

---

## ADR-022: n8n as orchestration only

**Decision:** n8n never contains Briefly business logic. It calls secret-authenticated FastAPI webhooks (`N8N_WEBHOOK_SECRET` via `X-Briefly-N8N-Secret`). `OrchestrationService` runs per-provider sync with failure isolation, then optionally regenerates Morning Brief / Weekly Digest. Unconfigured secret → `503`; bad secret → `401`. No unauthenticated admin endpoints.

**Why:**
- FastAPI + PostgreSQL remain the system of record
- One provider outage must not abort Calendar / Gmail / Notion / GHL / brief steps
- Secrets stay server-side; n8n only holds the shared webhook secret

**How it shows up:**
- `POST /webhooks/n8n/run|daily|weekly`
- Docs: `automation/n8n-daily-brief.md`

---

## ADR-024: Integrations page uses a canonical catalog

**Decision:** `GET /integrations` is built from `integration_catalog.SUPPORTED_INTEGRATIONS` merged with the authenticated user's `integrations` rows. Missing providers appear as `not-connected` with catalog display metadata only. Google OAuth (`provider=google`) projects onto both `google-calendar` and `gmail` cards. Demo users may overlay curated `demo_data.INTEGRATIONS` connection state for catalog entries that lack a user row. Real users never receive another user's tokens, accounts, or sync timestamps.

**Why:** New OAuth users previously only saw providers they had already connected, which hid Connect actions for Notion/GHL/monday/ClickUp.

---

## ADR-023: monday.com + ClickUp via shared WorkItem model

**Decision:** monday.com and ClickUp use the shared `OAuthProvider` registry and encrypt tokens on `Integration(provider=monday|clickup)`. Synced tasks land in a provider-neutral `work_items` table (migration `012`) with unique `(user_id, provider, external_id)`. `MondaySyncService` / `ClickUpSyncService` own API I/O; `WorkItemService` is the only read path for Overview / AI / Weekly Digest colour. AI never calls monday/ClickUp directly. Local `intelligence` is preserved on sync. Providers are independently optional.

**Auth:**
- monday.com: documented OAuth Authorization Code (`auth.monday.com`) with scopes `me:read boards:read workspaces:read account:read`. Legacy long-lived tokens (no refresh) — OAuth 2.1/PKCE deferred until architecture supports code_verifier storage.
- ClickUp: OAuth Authorization Code (`app.clickup.com/api`); no granular scopes; users pick Workspaces; tokens currently do not expire.

**Why:**
- Avoids duplicate monday/ClickUp domain models
- Reuses Fernet token storage and connect-while-signed-in guards
- Disconnected providers leave Overview / Brief / Ask contracts unchanged

**How it shows up:**
- Env: `MONDAY_CLIENT_*`, `CLICKUP_CLIENT_*`
- `POST /integrations/monday/sync`, `POST /integrations/clickup/sync`
- AI context key `workItems` with source attribution `monday.com` / `ClickUp`
