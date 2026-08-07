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

## v1.0.1 — Authentication foundation (Current)

**Status:** Complete (password auth; Google OAuth deferred)

- [x] Register / login / logout / refresh / me
- [x] JWT access tokens + rotating opaque refresh tokens
- [x] Password hashing (bcrypt); nullable `hashed_password` for future OAuth
- [x] `get_current_user` dependency on all domain routes
- [x] Demo fallback when `AUTH_REQUIRED=false` (portfolio unchanged)
- [x] Per-user scoping in services; `daily_briefs.user_id` migration

**Goal:** A clean auth layer integrations and Google OAuth can plug into without rewriting domain services.

---

## v1.1 — Google Calendar

**Target:** Q3 2026

- [ ] Google OAuth2 with `calendar.readonly`
- [ ] `integrations/google_calendar.py`
- [ ] Event sync into `Meeting`
- [ ] Attendee enrichment from contact history
- [ ] Preparation status derived from real signals: reschedules, late attendees, thread silence
- [ ] Free-time detection feeding the suggested focus blocks

**Goal:** Meeting intelligence built on a real calendar.

---

## v1.2 — Gmail

**Target:** Q3 2026

- [ ] Google OAuth2 with `gmail.readonly`
- [ ] `integrations/gmail.py`
- [ ] Thread sync into `Email`
- [ ] Categorisation into needs-reply, high-priority, waiting, delegated, informational
- [ ] Per-thread summary, priority and suggested response
- [ ] Waiting-on detection from send/receive history
- [ ] Reading-time estimation

**Goal:** An inbox the executive can act on without opening Gmail.

---

## v1.3 — OpenAI generation

**Target:** Q4 2026

- [ ] `integrations/openai.py` with structured output
- [ ] Brief assembly from synced meetings, threads and opportunities
- [ ] Retrieval-backed citations — sources come from records, not the model
- [ ] Ask Briefly answers generated against the same corpus
- [ ] Confidence scoring from retrieval coverage
- [ ] Cost and latency instrumentation per brief

**Goal:** The brief is genuinely generated, and every claim traces to a record.

---

## v1.4 — GoHighLevel and Notion

**Target:** Q4 2026

- [ ] `integrations/gohighlevel.py` — opportunity sync into `Opportunity`
- [ ] Risk scoring from engagement recency, stage movement and thread signals
- [ ] `integrations/notion.py` — page indexing for internal context
- [ ] Team-blocker detection from documents awaiting approval

**Goal:** Client risk and team blockers derived from real systems.

---

## v1.5 — n8n scheduling

**Target:** Q1 2027

- [ ] `integrations/n8n.py` webhook handlers
- [ ] Scheduled generation before the executive's configured delivery time
- [ ] Delivery to email and push on completion
- [ ] Retry and partial-source degradation (generate from three systems if the fourth is down)
- [ ] Sync failure alerting on the Integrations page

**Goal:** The brief is waiting every morning without anyone triggering it.

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
| v1.1 | Meeting intelligence | Google Calendar |
| v1.2 | Inbox intelligence | Gmail |
| v1.3 | Real generation | OpenAI |
| v1.4 | Client risk and context | GoHighLevel, Notion |
| v1.5 | Scheduled delivery | n8n |
| v2.0 | Multi-tenant production | All, plus auth |
