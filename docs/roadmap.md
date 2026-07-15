# Relay Roadmap

## v0.1 — UI with Mock Backend (Current)

**Status:** In progress

- [x] React frontend with all executive workspace pages
- [x] FastAPI backend with mock data endpoints
- [x] SQLAlchemy models and Alembic migrations
- [x] Pydantic schemas matching frontend contracts
- [x] Service layer architecture
- [x] Health check endpoint
- [x] CORS, logging, dependency injection
- [ ] Connect frontend to backend API
- [ ] Deploy backend to Railway
- [ ] Seed database with demo data

**Goal:** End-to-end demo with the frontend consuming the real backend API (still serving mock data).

---

## v0.2 — Google Calendar Integration

**Target:** Q3 2026

- [ ] Google OAuth2 flow for calendar access
- [ ] `integrations/google_calendar.py` module
- [ ] Sync calendar events into `Meeting` table
- [ ] `CalendarService` queries live data from database
- [ ] Overview and Daily Brief use synced meetings
- [ ] Meeting conflict detection and free-time analysis

**Goal:** Real calendar data powering the schedule views and daily briefings.

---

## v0.3 — Gmail Integration

**Target:** Q3 2026

- [ ] Google OAuth2 flow for Gmail access
- [ ] `integrations/gmail.py` module
- [ ] Email sync into `Email` table
- [ ] AI classification into executive categories (urgent, clients, investors, etc.)
- [ ] Executive summaries for each email
- [ ] `InboxService` serves live classified inbox
- [ ] Unread count and action-required flags

**Goal:** Real inbox with AI-powered executive email triage.

---

## v0.4 — GoHighLevel Integration

**Target:** Q4 2026

- [ ] GoHighLevel API connection
- [ ] `integrations/gohighlevel.py` module
- [ ] Sync deals/opportunities into `CRMDeal` table
- [ ] `CRMService` serves live pipeline data
- [ ] AI deal summaries via OpenAI
- [ ] Pipeline value calculations and stage tracking

**Goal:** Live CRM pipeline replacing mock deal data.

---

## v0.5 — OpenAI Executive Briefing

**Target:** Q4 2026

- [ ] `integrations/openai.py` module
- [ ] AI-generated daily brief from calendar, inbox, CRM, and projects
- [ ] Executive summary on overview dashboard
- [ ] AI recommendations based on real business context
- [ ] Assistant chat powered by GPT with tool access
- [ ] Email and deal summarization

**Goal:** Genuine AI intelligence across all workspace features.

---

## v0.6 — Make.com Orchestration

**Target:** Q1 2027

- [ ] `integrations/make.py` webhook handlers
- [ ] Scheduled daily brief generation workflow
- [ ] Email → classify → notify → CRM task automation
- [ ] ClickUp project sync (`integrations/clickup.py`)
- [ ] Cross-service workflow triggers
- [ ] Error handling and retry logic

**Goal:** Automated workflows connecting all business tools without manual intervention.

---

## v1.0 — Production AI Executive Partner

**Target:** Q2 2027

- [ ] User authentication (JWT)
- [ ] Multi-tenant support
- [ ] Notion knowledge base integration
- [ ] Real-time notifications
- [ ] Mobile-responsive optimizations
- [ ] Production monitoring and alerting
- [ ] Rate limiting and API security
- [ ] Billing and subscription management
- [ ] Onboarding flow for new executives

**Goal:** Production-ready SaaS that executives can use daily to run their business.

---

## Version Summary

| Version | Focus | Key Integration |
|---------|-------|-----------------|
| v0.1 | Mock backend + frontend | None |
| v0.2 | Calendar | Google Calendar |
| v0.3 | Inbox | Gmail |
| v0.4 | CRM | GoHighLevel |
| v0.5 | AI Intelligence | OpenAI |
| v0.6 | Automation | Make.com, ClickUp |
| v1.0 | Production SaaS | All integrations + auth |
