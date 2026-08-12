# Briefly API Reference

Base URL: `http://localhost:8000` (development)

All responses are JSON in camelCase, matching the frontend contract exactly. Interactive documentation is available at `/docs` (Swagger) and `/redoc`.

Field values marked *signal* use one shared vocabulary across the whole API: `critical`, `high`, `medium`, `low`.

Sources cited by the AI are one of: `Gmail`, `Google Calendar`, `GoHighLevel`, `Notion`, `OpenAI`, `n8n`.

Generation uses OpenAI when `OPENAI_API_KEY` is set (`OPENAI_MODEL`, `OPENAI_EMBED_MODEL`, `OPENAI_TIMEOUT_SECONDS` optional). API response contracts do not change when the key is absent — curated failover keeps the same shapes.

Notion OAuth uses `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, and `NOTION_REDIRECT_URI`. When unset, Notion start returns `503` and Overview / Brief / Ask keep their pre-Notion behaviour. Connect Notion while signed in so the workspace bot links to your Briefly user.

GoHighLevel OAuth uses `GHL_CLIENT_ID`, `GHL_CLIENT_SECRET`, and `GHL_REDIRECT_URI` (Marketplace Location app). When unset, GHL start returns `503`. Sync via `POST /integrations/gohighlevel/sync`.

n8n calls `POST /webhooks/n8n/*` with header `X-Briefly-N8N-Secret` matching `N8N_WEBHOOK_SECRET`. Unconfigured secret → `503`; wrong secret → `401`. See [automation/n8n-daily-brief.md](../automation/n8n-daily-brief.md).

monday.com OAuth uses `MONDAY_CLIENT_ID`, `MONDAY_CLIENT_SECRET`, `MONDAY_REDIRECT_URI`. ClickUp uses `CLICKUP_CLIENT_ID`, `CLICKUP_CLIENT_SECRET`, `CLICKUP_REDIRECT_URI`. Sync via `POST /integrations/monday/sync` and `POST /integrations/clickup/sync` into `work_items`. Connect while signed in.

---

## Health

### `GET /health`

```json
{ "status": "healthy" }
```

---

## Authentication

Password accounts issue a short-lived JWT access token and an opaque refresh token. Send the access token as `Authorization: Bearer <accessToken>` on subsequent requests.

When `AUTH_REQUIRED` is `false` (default), requests without a Bearer token resolve to the demo user so the portfolio product behaves as before. When `AUTH_REQUIRED` is `true`, missing or invalid tokens return `401`.

Demo login (after seed / first request that creates the demo user): email `lydia@arcadiasystems.com`, password from `DEMO_USER_PASSWORD` (default `briefly-demo`).

### `POST /auth/register`

Creates an account and returns tokens. Status `201`.

```json
{
  "email": "founder@example.com",
  "password": "secure-pass-99",
  "fullName": "Alex Founder",
  "name": "Alex",
  "role": "CEO",
  "company": "Example Co",
  "timezone": "UTC"
}
```

### `POST /auth/login`

```json
{ "email": "founder@example.com", "password": "secure-pass-99" }
```

### `POST /auth/refresh`

Rotates the refresh token (previous value is revoked).

```json
{ "refreshToken": "…" }
```

### `POST /auth/logout`

Revokes the refresh token. Status `204`. Body: `{ "refreshToken": "…" }`.

### Token response shape (`register` / `login` / `refresh`)

```json
{
  "accessToken": "eyJ…",
  "refreshToken": "…",
  "tokenType": "bearer",
  "expiresIn": 1800,
  "user": {
    "name": "Alex",
    "fullName": "Alex Founder",
    "role": "CEO",
    "company": "Example Co",
    "email": "founder@example.com",
    "avatar": "AF",
    "timezone": "UTC"
  }
}
```

### `GET /auth/me`

Current user. With Bearer → that user. Without Bearer and `AUTH_REQUIRED=false` → demo user.

---

## OAuth providers

Provider routes are generic: `/auth/oauth/{provider}/…` for `google`, `notion`, `gohighlevel`, `monday`, and `clickup`.

## Google OAuth

Identity + Calendar/Gmail scopes via Authorization Code Flow.

Requires `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`. When unset, start returns `503` and the portfolio demo continues to work without Google (`AUTH_REQUIRED=false`).

Scopes requested today: `openid`, `email`, `profile`, `calendar.readonly`, and `gmail.readonly`.

Existing Google connections granted before Calendar/Gmail sync must reconnect once to pick up the new scopes.

### `GET /auth/oauth/google/start`

Returns the Google authorize URL and CSRF `state`. Optional `Authorization: Bearer` links the eventual Google account to the already-authenticated user.

```json
{
  "provider": "google",
  "authorizationUrl": "https://accounts.google.com/o/oauth2/v2/auth?…",
  "state": "…"
}
```

### `GET /auth/oauth/google/callback`

Google redirects here with `?code=&state=`. Verifies state (single-use), exchanges the code, loads the Google profile, find-or-creates a `User`, stores encrypted provider tokens on `integrations` (`provider=google`), and issues the same Briefly JWT + refresh token response as password login.

If `OAUTH_SUCCESS_REDIRECT` is set, responds with `302` to that URL with `?ticket=…&provider=google` instead of JSON.

### `POST /auth/oauth/google/exchange`

Exchanges a one-time callback ticket for `TokenResponse`.

```json
{ "ticket": "…" }
```

### `GET /auth/oauth/google/status`

Connection status for the current user (Bearer or demo fallback).

### `POST /auth/oauth/google/refresh`

Refreshes the **Google** access token (not the Briefly JWT). Returns `{ "provider": "google", "accessToken": "…" }`.

### `POST /auth/oauth/google/disconnect`

Clears stored Google tokens for the current user.

## Notion OAuth

Workspace bot Authorization Code Flow. Connect while signed in so the bot links to your Briefly user (Notion may not expose a person email).

Requires `NOTION_CLIENT_ID`, `NOTION_CLIENT_SECRET`, and `NOTION_REDIRECT_URI`. When unset, start returns `503`. Tokens are long-lived (`expires_at` null); `POST /auth/oauth/notion/refresh` returns the stored access token without calling Notion.

Same route shapes as Google (`/start`, `/callback`, `/exchange`, `/status`, `/refresh`, `/disconnect`) with `provider=notion`. Callback stores encrypted tokens on `Integration(provider=notion)`. Sync via `POST /integrations/notion/sync`.

## GoHighLevel OAuth

Marketplace Authorization Code Flow (Location token). Connect while signed in so the location links to your Briefly user (synthetic `@users.gohighlevel.local` emails do not auto-provision users).

Requires `GHL_CLIENT_ID`, `GHL_CLIENT_SECRET`, and `GHL_REDIRECT_URI`. When unset, start returns `503`. Tokens are Fernet-encrypted on `Integration(provider=gohighlevel)`. Location id / user id from the token payload are stored under `integrations.config.ghl`.

Same route shapes as Google with `provider=gohighlevel`. Sync via `POST /integrations/gohighlevel/sync` → `GHLSyncService` upserts `Opportunity` rows (`external_id=ghl:{opportunityId}`), preserves local AI/risk/preparation fields, and marks missing open deals closed.

CRM intelligence (`crm_intelligence.derive_crm_signals`) derives at-risk / stale / upcoming-close / follow-up / high-value signals from synced rows for AI context — never invents CRM facts.

## monday.com OAuth

Authorization Code Flow via `https://auth.monday.com/oauth2/authorize`. Connect while signed in. Scopes: `me:read`, `boards:read`, `workspaces:read`, `account:read`. Tokens are Fernet-encrypted on `Integration(provider=monday)` and currently long-lived (no refresh). Sync: `POST /integrations/monday/sync` → `MondaySyncService` upserts `WorkItem` rows (`external_id=monday:{itemId}`), preserves `intelligence`, archives missing items on full sync.

## ClickUp OAuth

Authorization Code Flow via `https://app.clickup.com/api`. Users select Workspaces at consent (no granular scopes). Tokens are Fernet-encrypted on `Integration(provider=clickup)` and currently do not expire. Sync: `POST /integrations/clickup/sync` → `ClickUpSyncService` upserts `WorkItem` rows (`external_id=clickup:{taskId}`), incremental via `date_updated_gt` watermark, preserves `intelligence`.

---

## n8n orchestration webhooks

Secret-authenticated. No user JWT. Header:

```http
X-Briefly-N8N-Secret: <N8N_WEBHOOK_SECRET>
```

### `POST /webhooks/n8n/run`

```json
{
  "userEmail": "lydia@arcadiasystems.com",
  "providers": ["google-calendar", "gmail", "notion", "gohighlevel"],
  "regenerateMorningBrief": false,
  "regenerateWeeklyDigest": false
}
```

Each provider sync is isolated (`success` / `skipped` / `error`). One failure does not abort the others.

### `POST /webhooks/n8n/daily`

Syncs all providers + regenerates Morning Brief.

### `POST /webhooks/n8n/weekly`

Syncs all providers + regenerates Weekly Digest.

### `POST /webhooks/n8n/email-follow-up`

Triage **one** email for executive action using Briefly's existing `AIService`.

- Analysis only — never sends mail, never creates tasks, never mutates inbox.
- Authenticate with `X-Briefly-N8N-Secret` (same as other n8n webhooks).
- Malformed / unavailable AI → `502` with a generic message (no provider details).

**Request**

```json
{
  "message_id": "gmail-msg-123",
  "thread_id": "gmail-thread-456",
  "sender": "partner@client.com",
  "subject": "Can we meet Thursday?",
  "received_at": "2026-08-11T08:00:00Z",
  "body": "Would you be free Thursday 10:00 for a 30-minute sync?"
}
```

**Response**

```json
{
  "requires_action": true,
  "priority": "medium",
  "category": "meeting_request",
  "action": "Confirm or decline the proposed meeting time",
  "deadline": null,
  "reason": "Sender requests a meeting and asks for availability.",
  "suggested_response": "Happy to meet — Thursday 10:00 works on my side.",
  "confidence": 0.84
}
```

Promotional / newsletter / generic marketing mail should normally return `requires_action: false`. Approvals, information requests, meeting requests, and explicit deadlines should normally return `requires_action: true`. Deadlines are only returned when explicitly stated in the email.

---

## Workspace

### `GET /workspace`

Lightweight payload for the application shell. Fetched once by the layout rather than by each page.

`brief` freshness comes from `MorningBriefService.get_brief_meta()` (today's `morning_briefs` row when present, otherwise curated `BRIEF_META`). Badge counts are derived from `InboxService` / `MeetingService` / `CRMService`.

```json
{
  "user": {
    "name": "Lydia",
    "fullName": "Lydia K.",
    "role": "Founder & CEO",
    "company": "Arcadia Systems",
    "email": "lydia@arcadiasystems.com",
    "avatar": "LK",
    "timezone": "Europe/Athens"
  },
  "brief": {
    "id": "brief_2026_08_04",
    "date": "Tuesday, August 4, 2026",
    "generatedAt": "2026-08-04T06:30:00+03:00",
    "generatedLabel": "2 minutes ago",
    "confidence": "high",
    "sources": ["Gmail", "Google Calendar", "GoHighLevel", "Notion"],
    "headline": "Meridian Labs is the day…"
  },
  "badges": { "inbox": 5, "meetings": 4, "crm": 2 }
}
```

---

## Overview

### `GET /overview`

The executive dashboard: identity, brief provenance, the hero summary, four KPIs, recent activity and three recommendations.

**Partial PostgreSQL migration (Phase 1):** `executiveSummary.summary`, `.priorities` and `.risks` are read from the `daily_briefs` table when a row exists there, and fall back to curated data otherwise — including if the database itself is unreachable. Every other field on this page is still curated data. See [`GET /daily-brief/latest`](#daily-brief) and `OverviewService` for the mechanics.

```json
{
  "user": { "…": "see /workspace" },
  "brief": { "…": "see /workspace" },
  "executiveSummary": {
    "summary": "Meridian Labs has gone quiet for nine days…",
    "priorities": [
      {
        "id": "pri_1",
        "rank": 1,
        "title": "Decide the Meridian Labs renewal position before the 11:00 call",
        "detail": "Nine days of silence, a competitor quote in the thread…",
        "urgency": "critical",
        "owner": "Lydia",
        "source": "GoHighLevel"
      }
    ],
    "risks": [
      {
        "id": "risk_1",
        "title": "Meridian Labs renewal is being competitively shopped",
        "detail": "Their VP of Engineering forwarded a competitor pricing sheet…",
        "severity": "critical",
        "impact": "$480K ARR",
        "mitigation": "Lead with the migration cost analysis, not a discount.",
        "source": "Gmail"
      }
    ],
    "meetingsToPrepare": [
      {
        "id": "mtg_2",
        "title": "Meridian Labs — Renewal Negotiation",
        "time": "11:00",
        "reason": "Competitive threat surfaced last night. No agreed position yet."
      }
    ],
    "clientsNeedingAttention": [
      {
        "id": "cli_1",
        "company": "Meridian Labs",
        "stage": "Renewal",
        "value": "$480K",
        "lastContact": "9 days of silence, broken last night",
        "reason": "Competitively re-tendered by a new procurement lead…",
        "recommendedAction": "Hold price, trade on term length…",
        "severity": "critical"
      }
    ],
    "recommendedActions": [
      {
        "id": "act_foc_1",
        "label": "Hold price with Meridian, trade on term length",
        "rationale": "Competitor quote is 30% lower but excludes migration and support."
      }
    ]
  },
  "kpis": [
    {
      "id": "inbox",
      "label": "Inbox",
      "value": "6",
      "sublabel": "need your reply",
      "change": "18 handled by rules",
      "trend": "down",
      "icon": "inbox",
      "tone": "primary"
    }
  ],
  "activity": [
    {
      "id": "act_1",
      "type": "email",
      "title": "James Liu forwarded a competitor pricing sheet",
      "detail": "Meridian Labs · renewal thread",
      "time": "22:14 yesterday",
      "source": "Gmail"
    }
  ],
  "focus": [
    {
      "id": "foc_1",
      "title": "Hold price with Meridian, trade on term length",
      "description": "Their switching cost is roughly seven months…",
      "rationale": "Competitor quote is 30% lower but excludes migration and support.",
      "action": "Open the prep brief",
      "actionTarget": "/meetings",
      "impact": "$480K ARR protected",
      "priority": "critical",
      "sources": ["Gmail", "GoHighLevel"]
    }
  ]
}
```

**KPI icons:** `inbox`, `meetings`, `deals`, `tasks` · **trend:** `up`, `down`, `neutral` · **tone:** `primary`, `accent`, `slate`

**Activity types:** `email`, `deal`, `document`, `meeting`

---

## Daily Brief

<a id="daily-brief"></a>

### `GET /daily-brief/latest`

Direct read of the newest row in `daily_briefs` — the table backing part of `/overview` (see above). Unlike `/overview`, this endpoint does **not** fall back to curated data: it exists to show what is actually in PostgreSQL, so a missing brief or an unreachable database is a real error here.

```json
{
  "id": "1f9d7e2a-6b3c-4e21-9a0e-6a2f8c9d1b44",
  "generatedAt": "2026-08-04T06:30:00+00:00",
  "summary": "Meridian Labs has gone quiet for nine days…",
  "priorities": [{ "…": "PrioritySchema, same shape as /overview" }],
  "risks": [{ "…": "RiskSchema, same shape as /overview" }],
  "recommendations": [
    { "id": "rec_1", "title": "Send the Meridian migration-cost analysis before the 11:00 call", "rationale": "Reframes the conversation around switching cost instead of price." }
  ],
  "executiveScore": 74,
  "createdAt": "2026-08-04T06:30:01+00:00"
}
```

- **404** — no `DailyBrief` has been inserted yet (seed one with `backend/scripts/seed_daily_brief.py`)

`recommendations` and `executiveScore` are persisted but not yet read by `/overview` — they are reserved for a later migration phase.

---

## Morning Brief

### `GET /morning-brief`

The full briefing. Nine sections plus a closing answer, in reading order.

**PostgreSQL migration (Phase 7):** the report itself — `meta` (except `date`, which is derived from `brief_date`), `executiveSummary`, `topPriorities`, `criticalRisks`, `clientsNeedingAttention`, `suggestedFocus`, `recommendedDelegation` and `closing` — is read from the `morning_briefs` table for today's row, and `actionChecklist` from `brief_actions`. If no row exists for today (empty table) or PostgreSQL is unreachable, this generates today's brief from curated data and tries to persist it, so the next request finds a real row. If that persistence attempt also fails — most likely `morning_briefs`/`brief_actions` do not exist in the connected database yet — the response falls all the way back to the pre-migration behaviour: every field straight from curated data, including the stable `chk_1`…`chk_6` checklist ids. `meetings` and `importantEmails` are not stored on `MorningBrief` — they are pulled live from `MeetingService`/`InboxService` on every call (Phase 6), so the brief never shows a meeting or email that has since changed elsewhere. See `MorningBriefService` for the mechanics. Seed data with `backend/scripts/seed_morning_brief.py`.

```json
{
  "meta": { "…": "brief provenance, see /workspace" },
  "preparedFor": { "…": "user" },
  "executiveSummary": "Meridian Labs has gone quiet for nine days…",
  "topPriorities": [ { "…": "priority objects, ranked" } ],
  "criticalRisks": [ { "…": "risk objects" } ],
  "meetings": [
    {
      "id": "mtg_2",
      "time": "11:00",
      "title": "Meridian Labs — Renewal Negotiation",
      "attendees": ["James Liu", "Dana Whitfield", "Elena Park"],
      "prepStatus": "needs-prep",
      "note": "Competitive threat surfaced last night. No agreed position yet."
    }
  ],
  "clientsNeedingAttention": [ { "…": "client attention objects" } ],
  "importantEmails": [
    {
      "id": "em_1",
      "sender": "James Liu",
      "subject": "Fwd: Vantage Cloud — commercial proposal",
      "summary": "Appears to be an accidental forward…",
      "priority": "critical",
      "waitingSince": "22:14 yesterday"
    }
  ],
  "suggestedFocus": {
    "headline": "Protect the morning…",
    "rationale": "You have 90 minutes of uninterrupted time…",
    "blocks": [
      {
        "id": "blk_1",
        "start": "09:30",
        "end": "10:45",
        "label": "Meridian renewal preparation",
        "reason": "Build the migration cost case and set your walk-away line.",
        "kind": "deep-work"
      }
    ]
  },
  "recommendedDelegation": [
    {
      "id": "del_1",
      "task": "Draft the July board metrics narrative",
      "assignee": "Sarah Chen",
      "assigneeRole": "CFO",
      "reason": "She wrote the underlying analysis…",
      "effort": "60 min saved"
    }
  ],
  "actionChecklist": [
    {
      "id": "chk_1",
      "label": "Set the Meridian walk-away price and term",
      "category": "Decision",
      "due": "Before 11:00",
      "done": false
    }
  ],
  "closing": {
    "question": "What should I accomplish today?",
    "answer": "Three things…",
    "bullets": ["Hold Meridian pricing and trade term length instead…"]
  }
}
```

**Focus block kinds:** `deep-work`, `decision`, `quick-win`, `review`

**Checklist categories:** `Decision`, `Reply`, `Delegate`, `Review`

### `POST /morning-brief/regenerate`

Re-runs generation against the latest data from every connected system. Returns the same shape as `GET /morning-brief` with refreshed `meta.generatedAt` and `meta.generatedLabel`.

Creates today's `MorningBrief` row if one does not exist yet, or replaces its report content if one does — but never recreates `BriefAction` rows for a brief that already has them, so regenerating the report never rewinds checklist progress the executive already made.

### `PATCH /morning-brief/checklist/{item_id}`


Marks a checklist item complete or incomplete. This is the only brief state the executive edits directly.

**Request:** `{ "done": true }`

**Response 200:** the updated checklist item. **404** if the item does not exist.

Updates the `BriefAction` row in PostgreSQL (setting `completedAt` when marked done, clearing it otherwise). If `item_id` is not a persisted `BriefAction` — most likely because persistence is not available yet — this falls back to mutating the curated `chk_1`…`chk_6` items in place, matching the pre-migration behaviour.

---

## Weekly Digest (Weekly Intelligence & Next Week Outlook)

Cross-system memory + forward outlook from **user-scoped persisted rows** only (Gmail `Email`, Google Calendar `Meeting`, GHL `Opportunity`, Notion `NotionItem`, monday/ClickUp `WorkItem`). Complements the Morning Brief (today) — it does not replace it.

Generation goes `WeeklyDigestService → AIService → OpenAIClient`. Cached per user on `(user_id, week_start)`. Sources with zero synced rows are omitted (connected ≠ usable). Demo curated content is never returned for authenticated non-demo users. When OpenAI is unavailable or fewer than 3 cross-system signals exist, a curated fallback is returned with `generatedBy: "curated"`. Email bodies are not stored — if only subject/metadata exists, `dataCoverage.emailNote` states the limited view.

### `GET /weekly-digest`

Returns the cached digest for the current rolling week, generating one if missing.

```json
{
  "id": "…",
  "weekStart": "2026-08-02",
  "weekEnd": "2026-08-08",
  "weekLabel": "Aug 2 – 8, 2026",
  "headline": "…",
  "summary": "…",
  "weekSummary": "…",
  "importantConversations": [
    {
      "id": "…",
      "title": "…",
      "detail": "…",
      "source": "Gmail",
      "emailIds": ["…"],
      "kind": "fact"
    }
  ],
  "decisionsAndApprovals": [],
  "followUps": [],
  "unresolvedItems": [],
  "notableActivity": [],
  "carryIntoNextWeek": [],
  "nextWeekOutlook": {
    "upcomingMeetings": [],
    "upcomingDeadlines": [],
    "overdueWork": [],
    "crmAttention": [],
    "emailFollowUps": [],
    "workItems": [],
    "carryForward": [],
    "recommendedPriorities": [],
    "risksAndWatchouts": [],
    "workloadSignals": []
  },
  "planningNote": "…",
  "confidence": "high",
  "generatedBy": "openai",
  "sources": ["Gmail", "Google Calendar", "OpenAI"],
  "emailCount": 12,
  "dataCoverage": {
    "emailCount": 12,
    "emailSummariesAvailable": true,
    "emailNote": "",
    "meetingCount": 3,
    "opportunityCount": 1,
    "workItemCount": 4,
    "notionItemCount": 0,
    "sourcesWithData": ["Gmail", "Google Calendar", "GoHighLevel"]
  },
  "generatedAt": "2026-08-08T10:00:00+00:00",
  "generatedLabel": "just now"
}
```

### `POST /weekly-digest/regenerate`

Forces a fresh digest for the current week window (overwrites the cached row).

---

## Inbox

**PostgreSQL + Gmail:** emails are read from the `emails` table when rows exist for the current user, and fall back to curated data otherwise. When Google is connected, `GmailSyncService` writes messages into `Email` (`external_id=gmail:{messageId}`) with Gmail labels and thread ids — no AI summarisation. `InboxService` is unchanged. `summary` remains curated aggregate stats for now. Seed curated rows with `backend/scripts/seed_emails.py`.

### `GET /inbox`

Summarised threads grouped into executive categories.

```json
{
  "summary": {
    "headline": "Six emails genuinely need you. The other eighteen do not.",
    "totalUnread": 24,
    "estimatedClearTime": "34 min",
    "handledAutomatically": 18
  },
  "categories": [
    {
      "id": "needs-reply",
      "label": "Needs Reply",
      "description": "Waiting on a response from you",
      "count": 3
    }
  ],
  "emails": [
    {
      "id": "em_1",
      "category": "high-priority",
      "subject": "Fwd: Vantage Cloud — commercial proposal",
      "sender": {
        "name": "James Liu",
        "email": "james.liu@meridianlabs.com",
        "company": "Meridian Labs",
        "avatar": "JL"
      },
      "timeLabel": "22:14 yesterday",
      "receivedAt": "2026-08-03T22:14:00+03:00",
      "aiSummary": "Appears to be an accidental forward…",
      "priority": "critical",
      "suggestedResponse": "Acknowledge receipt without commenting…",
      "readingTime": "3 min",
      "threadCount": 7,
      "unread": true,
      "labels": ["Renewal", "Meridian Labs"]
    }
  ]
}
```

**Categories:** `needs-reply`, `high-priority`, `waiting`, `delegated`, `informational`

`suggestedResponse` is a draft for approval. The API has no send endpoint by design.

---

## Meetings

**PostgreSQL + Google Calendar:** meetings are read from the `meetings` table when rows exist for the current user, and fall back to curated data otherwise (demo user / empty table / DB unreachable). When Google is connected, `CalendarSyncService` writes primary-calendar events into `Meeting` (`external_id=primary:{eventId}`); `MeetingService` is unchanged. Seed curated rows with `backend/scripts/seed_meetings.py`.

### `GET /meetings`

```json
{
  "date": "Tuesday, August 4, 2026",
  "meetingCount": 4,
  "needsPreparation": 2,
  "totalScheduledMinutes": 165,
  "meetings": [
    {
      "id": "mtg_2",
      "title": "Meridian Labs — Renewal Negotiation",
      "startTime": "11:00",
      "endTime": "11:45",
      "duration": "45 min",
      "type": "client",
      "location": "Zoom",
      "prepStatus": "needs-prep",
      "prepReason": "Competitive threat surfaced last night…",
      "attendees": [
        { "name": "James Liu", "role": "VP Engineering", "company": "Meridian Labs", "avatar": "JL" }
      ],
      "agenda": ["Renewal term and pricing"],
      "company": {
        "name": "Meridian Labs",
        "industry": "Industrial R&D software",
        "size": "1,200 employees",
        "relationship": "Customer since March 2023",
        "arr": "$480K",
        "background": "Three-year customer, 94% seat utilisation…"
      },
      "relatedEmails": [
        {
          "id": "rel_2",
          "subject": "Fwd: Vantage Cloud — commercial proposal",
          "sender": "James Liu",
          "summary": "Competitor quote at roughly 30% below current pricing…",
          "time": "22:14 yesterday"
        }
      ],
      "preparationNotes": ["Their competitor quote omits migration…"],
      "talkingPoints": ["Migration cost estimate: roughly seven months…"],
      "recommendedQuestions": ["What does the evaluation look like if we take price off the table?"],
      "risks": [
        {
          "title": "Discounting sets the floor for two other renewals",
          "detail": "Globex and Northwind renew in Q4…",
          "severity": "critical"
        }
      ],
      "sources": ["Gmail", "Google Calendar", "GoHighLevel"]
    }
  ]
}
```

**Meeting types:** `internal`, `client`, `investor`, `personal` · **prepStatus:** `ready`, `needs-prep`

### `GET /meetings/{meeting_id}`

A single meeting object. **404** if it does not exist.

---

## CRM

**Partial PostgreSQL migration (Phase 4):** `opportunities` (and the pipeline totals derived from them) are read from the `opportunities` table when rows exist there, and fall back to curated data otherwise — including if the database itself is unreachable. Same fallback shape as `MeetingService`/`InboxService`; see `CRMService.list_opportunities()` for the mechanics. Seed data with `backend/scripts/seed_opportunities.py`.

### `GET /crm`

Only opportunities that warrant executive attention, plus pipeline totals.

```json
{
  "summary": {
    "pipelineValue": 2595000,
    "weightedValue": 1604500,
    "needingAttention": 2,
    "closingThisMonth": 2,
    "headline": "2 opportunities worth $755K need you…"
  },
  "opportunities": [
    {
      "id": "opp_1",
      "company": "Meridian Labs",
      "logo": "ML",
      "industry": "Industrial R&D software",
      "stage": "Renewal",
      "value": 480000,
      "probability": 55,
      "owner": "Elena Park",
      "closeDate": "Aug 7, 2026",
      "riskLevel": "critical",
      "lastInteraction": {
        "type": "email",
        "summary": "Competitor pricing sheet forwarded by their champion",
        "time": "22:14 yesterday"
      },
      "aiSummary": "A three-year customer at 94% utilisation…",
      "recommendedAction": "Hold price and offer a 36-month term…",
      "signals": ["Champion still engaged", "94% utilisation"],
      "sources": ["GoHighLevel", "Gmail"]
    }
  ]
}
```

---

## Ask Briefly

### `GET /ask`

Suggested executive questions, recent history and the systems currently readable.

`recent` is served from persisted `ask_reports` when present; the demo user falls back to curated recent questions when history is empty. Response shape is unchanged.

```json
{
  "suggestions": [
    {
      "id": "sug_1",
      "question": "What should I prioritize today?",
      "category": "Prioritisation",
      "icon": "target"
    }
  ],
  "recent": [
    { "id": "rec_1", "question": "Which deals are most at risk?", "askedAt": "Yesterday, 17:40" }
  ],
  "connectedSources": ["Google Calendar", "Gmail", "Notion", "GoHighLevel", "OpenAI"]
}
```

**Suggestion icons:** `target`, `calendar`, `trending`, `activity`, `pen`, `users`

### `POST /ask`

**Request:** `{ "question": "Which deals are most at risk?" }` (1–500 characters)

**Response 200:** a cited report, never a chat message. Generated via `AIService` when OpenAI is available; otherwise the curated report library. Every answer is persisted for `GET /ask` recent history when the database is available.

```json
{
  "id": "rep_9f2c41ad8b0e",
  "question": "Which deals are most at risk?",
  "answeredAt": "2026-08-04T08:12:04+00:00",
  "summary": "Two of six opportunities are genuinely at risk…",
  "confidence": "high",
  "sections": [
    {
      "id": "sec_1",
      "title": "At risk",
      "type": "ranked",
      "items": [
        {
          "title": "Meridian Labs — $480K renewal",
          "detail": "Competitively re-tendered. Probability fell 25 points overnight.",
          "meta": "Critical"
        }
      ],
      "body": null
    }
  ],
  "citations": [
    { "source": "GoHighLevel", "detail": "6 opportunities, $2.6M", "count": 6 }
  ],
  "followUps": ["Draft a follow-up email for Meridian Labs."]
}
```

**Section types:** `ranked` and `list` use `items`; `text` and `draft` use `body`.

Questions that do not match a known report fall back to a generic cited response rather than an error.

---

## Integrations

**PostgreSQL persistence:** `GET /integrations` always returns the canonical supported-provider catalog (Google Calendar, Gmail, Notion, GoHighLevel, monday.com, ClickUp, OpenAI, n8n) merged with the *current user's* `integrations` rows. Connection status, account, and last-sync metadata come only from that user's rows — never from another user. Providers without a user row appear as `not-connected`. Demo users may still overlay curated `demo_data` connection state when they lack a row. `syncHistory` comes from the user's `sync_events` (demo fallback when empty/unreachable). OAuth tokens stay Fernet-encrypted on `Integration.config.oauth` and are never returned in this payload. Manual sync routes unchanged. Seed with `backend/scripts/seed_integrations.py` then `seed_sync_events.py`.

### `GET /integrations`

```json
{
  "connectedCount": 4,
  "totalCount": 6,
  "integrations": [
    {
      "id": "gmail",
      "name": "Gmail",
      "category": "Email",
      "description": "Thread summarisation, prioritisation and suggested responses.",
      "status": "connected",
      "account": "lydia@arcadiasystems.com",
      "lastSync": "2026-08-04T06:29:00+03:00",
      "lastSyncLabel": "3 minutes ago",
      "scopes": ["gmail.readonly", "gmail.metadata"],
      "metrics": [{ "label": "Threads indexed", "value": "24" }],
      "poweredBy": "Google Workspace API"
    }
  ],
  "syncHistory": [
    {
      "id": "sync_2",
      "integrationId": "openai",
      "integration": "OpenAI",
      "event": "Morning brief generated",
      "status": "success",
      "time": "06:30",
      "detail": "4 sources, 18.4s, 2,140 tokens"
    }
  ]
}
```

**Integration status:** `connected`, `syncing`, `not-connected`, `error`

**Sync event status:** `success`, `running`, `warning`, `error`

### `POST /integrations/{integration_id}/sync`

Triggers a manual read and appends history. Returns the full `GET /integrations` payload.

For `google-calendar` / `gmail` / `google` when Google OAuth is connected: runs incremental Calendar and/or Gmail sync into `Meeting` / `Email` (idempotent upsert, deletes removed items, preserves local AI/prep fields when set).

For `notion` when Notion OAuth is connected: runs incremental Notion sync into `NotionItem` (search + selected databases, watermark on `last_edited_time`, archives deleted pages, preserves `intelligence`).

For `gohighlevel` when GHL OAuth is connected: runs opportunity sync into `Opportunity` (open/won/lost/abandoned, idempotent `external_id`, preserves AI/risk fields, closes missing open deals).

For `monday` / `clickup` when connected: runs work-item sync into `WorkItem` (idempotent upsert, archive missing on full sync, preserves `intelligence`).

- **404** — unknown integration
- **409** — not connected, or required scope missing (reconnect Google / Notion / GoHighLevel / monday / ClickUp)

### `POST /webhooks/google/calendar`

Google Calendar push notifications. Always returns `204`.

Headers: `X-Goog-Channel-ID`, `X-Goog-Resource-State`, `X-Goog-Resource-ID`.

The initial `sync` handshake is acknowledged without pulling events. Later notifications trigger the same incremental sync path as manual sync. Optional watch registration: set `GOOGLE_CALENDAR_WEBHOOK_URL` and call `CalendarSyncService.ensure_watch(user)`.

### `POST /webhooks/google/gmail`

Gmail Pub/Sub push notifications. Always returns `204`.

Body: standard Pub/Sub envelope; decoded `data` JSON includes `emailAddress` and optional `historyId`. Optional watch: set `GMAIL_PUBSUB_TOPIC` and call `GmailSyncService.ensure_watch(user)`.

---

## Settings

### `GET /settings`

Returns `profile`, `preferences`, `notifications`, `security`, `theme` and `connectedAccounts`.

Authenticated users receive their PostgreSQL `User` profile (not `demo_data.USER`). `profile.hasPassword` / `security.hasPassword` indicate whether password change is available (false for Google-only accounts with `hashed_password = NULL`).

```json
{
  "profile": {
    "fullName": "Lydia K.",
    "role": "Founder & CEO",
    "company": "Arcadia Systems",
    "email": "lydia@arcadiasystems.com",
    "phone": "+30 210 555 0148",
    "timezone": "Europe/Athens (GMT+3)",
    "avatar": "LK",
    "hasPassword": true
  },
  "preferences": {
    "briefTime": "06:30",
    "briefDays": ["Mon", "Tue", "Wed", "Thu", "Fri"],
    "tone": "Direct",
    "toneOptions": ["Direct", "Balanced", "Detailed"],
    "briefLength": "Standard",
    "briefLengthOptions": ["Concise", "Standard", "Comprehensive"],
    "focusAreas": ["Revenue", "Client risk", "Team blockers"],
    "focusAreaOptions": ["Revenue", "Client risk", "Team blockers", "Product", "Hiring", "Finance"],
    "autoApproveActions": false
  },
  "notifications": [
    {
      "id": "ntf_1",
      "label": "Morning brief ready",
      "description": "Sent when your brief finishes generating.",
      "channel": "Email",
      "enabled": true
    }
  ],
  "security": {
    "twoFactorEnabled": true,
    "twoFactorMethod": "Authenticator app",
    "lastPasswordChange": "March 12, 2026",
    "sessions": [
      {
        "id": "ses_1",
        "device": "MacBook Pro · Chrome",
        "location": "Athens, GR",
        "lastActive": "Active now",
        "current": true
      }
    ],
    "apiKeys": [
      {
        "id": "key_1",
        "label": "n8n automation",
        "prefix": "brf_live_9f2c",
        "createdAt": "June 2, 2026",
        "lastUsed": "Never"
      }
    ]
  },
  "theme": {
    "mode": "Light",
    "modeOptions": ["Light", "Dark", "System"],
    "density": "Comfortable",
    "densityOptions": ["Compact", "Comfortable"],
    "accent": "Emerald",
    "accentOptions": ["Emerald", "Slate", "Amber"],
    "reducedMotion": false
  },
  "connectedAccounts": [
    {
      "id": "acc_1",
      "provider": "Google",
      "detail": "lydia@arcadiasystems.com",
      "status": "connected",
      "connectedAt": "January 8, 2026"
    }
  ]
}
```

`autoApproveActions` is permanently `false`. Briefly does not act without approval.

### `PATCH /settings/preferences`

Partial update; omitted fields are left unchanged. Returns the full preferences object. `autoApproveActions` is ignored if supplied — the server will not let it be enabled.

```json
{ "tone": "Balanced", "focusAreas": ["Revenue", "Hiring"] }
```

### `PATCH /settings/notifications/{notification_id}`

**Request:** `{ "enabled": false }` — returns the updated notification. **404** if unknown.

### `PATCH /settings/profile` (implemented)

Updates `fullName`, `role`, `company`, `timezone`, and `avatar` (initials string only — no photo upload). Persists to PostgreSQL `users`. Returns `UserSchema` (same shape as `GET /auth/me`). AuthContext/UserMenu/Settings should refresh from this response without a full reload.

```json
{
  "fullName": "Lydia Real",
  "role": "CEO",
  "company": "Real Systems",
  "timezone": "Europe/Athens",
  "avatar": "LR"
}
```

### `POST /settings/password` (implemented for password accounts)

Requires `currentPassword` + `newPassword` (min 8). Hashes with bcrypt. Revokes **all** refresh tokens for the user. Returns `{ "ok": true, "message": "…" }`. Google/OAuth-only users (`hashed_password` null) receive **400** — they can edit profile without creating a password.

### Intentionally deferred (Settings)

- Profile photo file storage / upload
- Session/device revoke UI (beyond password-driven refresh revocation)
- Personal API key management
- Two-factor authentication
- Density / accent / reduce-motion persistence

---

## Errors

Standard FastAPI format:

```json
{ "detail": "Meeting 'mtg_9' not found" }
```

| Status | Meaning |
|--------|---------|
| 404 | Resource not found |
| 409 | Action conflicts with current state (e.g. syncing a disconnected integration) |
| 422 | Request body failed validation |
| 500 | Internal server error |
