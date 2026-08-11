# Briefly Roadmap

## v1.0 — Briefing platform on curated data

**Status:** Complete

- [x] Eight-page product focused on the Morning Brief
- [x] React frontend in JavaScript with a reusable card library
- [x] FastAPI backend: workspace, overview, brief, inbox, meetings, CRM, ask, integrations, settings
- [x] Shared urgency vocabulary across API and UI
- [x] Mutations: regenerate brief, checklist state, integration sync, preferences, notifications
- [x] Citations on every AI statement
- [x] Print-ready Morning Brief
- [x] Persistence schema aligned to the API contract

**Goal:** A complete, demonstrable product where only the upstream data is simulated.

---

## v1.0.1 — Authentication foundation

**Status:** Complete (password auth)

- [x] Register / login / logout / refresh / me
- [x] JWT access tokens + rotating opaque refresh tokens
- [x] Password hashing (bcrypt); nullable `hashed_password` for future OAuth
- [x] `get_current_user` dependency on all domain routes
- [x] Demo fallback when `AUTH_REQUIRED=false` (portfolio unchanged)
- [x] Per-user scoping in services; `daily_briefs.user_id` migration

**Goal:** A clean auth layer integrations and Google OAuth can plug into without rewriting domain services.

---

## v1.0.2 — Google OAuth identity

**Status:** Complete (identity + Calendar readonly scope)

- [x] Authorization Code Flow with CSRF state
- [x] Reusable `OAuthProvider` abstraction (`app/integrations/oauth/`)
- [x] Find-or-create `User`; issue existing JWT + refresh tokens
- [x] Encrypted Google tokens on `Integration(provider=google)`
- [x] Provider token refresh + disconnect
- [x] Demo mode preserved when Google is unconfigured

**Goal:** Sign in with Google and store tokens future Calendar/Gmail sync can reuse.

---

## v1.0.3 — Google Calendar sync

**Status:** Complete (events → `Meeting`; no OpenAI)

- [x] Incremental Calendar sync via `syncToken`
- [x] Idempotent upsert by `(user_id, external_id)`; cancelled events deleted
- [x] Preserve local prep / intelligence metadata on updates
- [x] Webhook endpoint `POST /webhooks/google/calendar` + optional watch registration
- [x] Manual sync via existing `POST /integrations/google-calendar/sync`
- [x] MeetingService unchanged — DB rows replace demo fallback when present

**Goal:** Real calendar events power Meetings when Google is connected.

---

## v1.0.4 — Gmail sync

**Status:** Complete (messages → `Email`; AI fields left empty for Phase 2.5)

- [x] Incremental Gmail sync via `historyId`
- [x] Idempotent upsert by `external_id=gmail:{messageId}`; deleted messages removed
- [x] Preserve Gmail labels; store provider message + thread ids
- [x] AI fields left empty for `AIService` fill (no overwrite of local edits)
- [x] Webhook endpoint `POST /webhooks/google/gmail` (Pub/Sub)
- [x] Manual sync via `POST /integrations/gmail/sync`
- [x] InboxService reads DB rows (replaces demo fallback when present)

**Goal:** Real inbox threads power Inbox when Google is connected.

---

## v1.0.5 — OpenAI integration

**Status:** Complete (Responses API + curated failover)

- [x] `app/integrations/openai.py` (Responses API, structured JSON)
- [x] `AIService` orchestration + `ai_prompts.py` templates/schemas
- [x] Morning Brief AI generation with row-level cache + regenerate
- [x] Meeting prep → `Meeting.intelligence` (never overwrite manual edits)
- [x] Email summary / priority / suggested response (empty fields only)
- [x] Ask Briefly AI answers + `ask_reports` history; curated failover
- [x] Failover on missing key, timeout, rate limit, unavailable, bad JSON
- [x] Mocked tests with no network access

**Goal:** Live generation when OpenAI is configured; identical demo behaviour when it is not.

---

## v1.1 — Google Calendar intelligence

**Target:** Q3 2026

- [x] Google OAuth2 with `calendar.readonly` + event sync into `Meeting`
- [x] OpenAI preparation generation for synced meetings (via `AIService`)
- [ ] Attendee enrichment from contact history
- [ ] Preparation status derived from real signals: reschedules, late attendees, thread silence
- [ ] Free-time detection feeding the suggested focus blocks

**Goal:** Meeting intelligence built on a real calendar.

---

## v1.2 — Gmail intelligence

**Target:** Q3 2026

- [x] Google OAuth2 with `gmail.readonly` + message sync into `Email`
- [x] Per-thread AI summary, priority and suggested response (lazy on detail)
- [ ] Categorisation into needs-reply, high-priority, waiting, delegated, informational (AI)
- [ ] Waiting-on detection from send/receive history
- [ ] Reading-time estimation from full bodies

**Goal:** An inbox the executive can act on without opening Gmail.

---

## v1.3 — OpenAI depth

**Target:** Q4 2026

- [x] `integrations/openai.py` with structured output
- [x] Brief assembly from synced meetings, threads and opportunities
- [x] Ask Briefly answers generated against the same corpus
- [ ] Retrieval-backed embeddings (`OPENAI_EMBED_MODEL`) for tighter citations
- [ ] Confidence scoring from retrieval coverage
- [ ] Cost and latency instrumentation per brief

**Goal:** Every claim traces to a retrieved record; generation is metered.

---

## v1.0.7 — Weekly Email Digest + dark-mode skeletons

**Status:** Complete (superseded by v1.7 cross-system outlook)

- [x] Theme-aware skeleton/shimmer (no hard-coded light greys in dark mode)
- [x] `GET/POST /weekly-digest` via `WeeklyDigestService` → `AIService`
- [x] `weekly_digests` persistence (migration `010`)
- [x] Frontend Weekly Digest page + quiet CTAs from Morning Brief / Overview

---

## v1.7 — Weekly Intelligence + editable profile (Current)

**Status:** Complete

- [x] Cross-system Weekly Digest context from persisted Email / Meeting / Opportunity / Notion / WorkItem (user-scoped)
- [x] Next Week Outlook (meetings, deadlines, overdue, CRM, follow-ups, recommendations) with fact vs recommendation kinds
- [x] Honest limited-email coverage when bodies/snippets are not stored
- [x] `PATCH /settings/profile` + `POST /settings/password` (bcrypt; revoke all refresh tokens)
- [x] Settings UI: editable profile + initials avatar; OAuth-only password state; dead session/API-key controls removed
- [x] Authenticated surfaces use DB `User` — never swap in `demo_data.USER`
- [ ] Profile photo upload / object storage (deferred)
- [ ] Session device management + personal API keys (deferred)

---

## v1.0.6 — Notion integration

**Status:** Complete (OAuth + incremental sync + AI/Overview wiring)

- [x] `NotionOAuthProvider` registered beside Google; encrypted tokens on `Integration`
- [x] `integrations/notion.py` (`NotionClient`) + `NotionSyncService` / `NotionService`
- [x] Sync tasks, projects, notes, decisions, meeting notes, selected databases
- [x] Incremental watermark (`last_edited_time`), idempotent upserts, preserve `intelligence`
- [x] Morning Brief + Ask retrieval context; Overview tasks / overdue / docs / projects
- [x] Failover: disconnected Notion leaves API contracts and demo behaviour unchanged
- [x] Mocked tests (OAuth, sync, deletes, upserts, fallback, Brief/Ask/Overview)

**Goal:** Internal Notion context powers the brief without changing the product surface when Notion is off.

---

## v1.4 — GoHighLevel CRM

**Status:** Complete (OAuth + opportunity sync + CRM intelligence)

- [x] `GoHighLevelOAuthProvider` + encrypted Location tokens on `Integration`
- [x] `integrations/gohighlevel.py` (`GHLClient`) + `GHLSyncService`
- [x] Idempotent `Opportunity` upserts (`external_id=ghl:…`), closed/missing handling
- [x] Preserve local AI / risk / preparation fields on sync
- [x] `crm_intelligence.derive_crm_signals` → AIService context (no fabricated CRM facts)
- [x] Integrations UI: Connect / Connected / Sync / last synced / error
- [x] Mocked tests (auth, connect, sync, upsert, AI preserve, scoping, failure)
- [ ] Historical stage-movement detection (needs stage history; deferred)
- [ ] Richer Notion team-blocker / database selection UI (separate)

**Goal:** Client risk derived from real GHL pipeline state.

---

## v1.5 — n8n orchestration

**Status:** Complete (secret webhooks + per-provider isolation)

- [x] `POST /webhooks/n8n/run|daily|weekly` with `X-Briefly-N8N-Secret`
- [x] `OrchestrationService` — sync providers then regenerate brief/digest
- [x] Partial failure isolation (one provider error does not abort the workflow)
- [x] Workflow docs in `automation/n8n-daily-brief.md`
- [ ] Delivery to email and push on completion
- [ ] Sync failure alerting on the Integrations page

**Goal:** The brief is waiting every morning without anyone triggering it.

---

## v1.6 — monday.com + ClickUp work management

**Status:** Complete (OAuth + WorkItem sync + AI/Overview wiring)

- [x] Shared `work_items` model + migration `012`
- [x] `MondayOAuthProvider` / `MondayClient` / `MondaySyncService`
- [x] `ClickUpOAuthProvider` / `ClickUpClient` / `ClickUpSyncService`
- [x] `WorkItemService` for Overview / Morning Brief / Weekly Digest / Ask
- [x] Integrations UI Connect / Sync / Disconnect
- [x] Mocked tests; independently optional providers
- [ ] monday.com OAuth 2.1 + PKCE when OAuthState stores code_verifier

---

## v2.0 — Multi-executive production

**Target:** Q2 2027

- [ ] JWT authentication and per-user integration tokens
- [ ] Multi-tenant isolation
- [ ] Brief history and week-over-week comparison
- [ ] Decision tracking: what was recommended, what was chosen, what happened
- [ ] Mobile brief reader
- [ ] Rate limiting, monitoring, billing

**Goal:** A production SaaS that measures whether its recommendations were right.

---

## Version Summary

| Version | Focus | Integration |
|---------|-------|-------------|
| v1.0 | Full product, curated data | None |
| v1.0.5 | OpenAI layer + failover | OpenAI |
| v1.0.6 | Notion OAuth + sync + context | Notion |
| v1.1 | Meeting intelligence | Google Calendar |
| v1.2 | Inbox intelligence | Gmail |
| v1.3 | Retrieval depth / metering | OpenAI embeddings |
| v1.4 | GHL CRM sync + intelligence | GoHighLevel |
| v1.5 | n8n orchestration webhooks | n8n |
| v2.0 | Multi-tenant production | All, plus auth |
