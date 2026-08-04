# Briefly API Reference

Base URL: `http://localhost:8000` (development)

All responses are JSON in camelCase, matching the frontend contract exactly. Interactive documentation is available at `/docs` (Swagger) and `/redoc`.

Field values marked *signal* use one shared vocabulary across the whole API: `critical`, `high`, `medium`, `low`.

Sources cited by the AI are one of: `Gmail`, `Google Calendar`, `GoHighLevel`, `Notion`, `OpenAI`, `n8n`.

---

## Health

### `GET /health`

```json
{ "status": "healthy" }
```

---

## Workspace

### `GET /workspace`

Lightweight payload for the application shell. Fetched once by the layout rather than by each page.

```json
{
  "user": {
    "name": "Lydia",
    "fullName": "Lydia Reyes",
    "role": "Founder & CEO",
    "company": "Arcadia Systems",
    "email": "lydia@arcadiasystems.com",
    "avatar": "LR",
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

## Morning Brief

### `GET /morning-brief`

The full briefing. Nine sections plus a closing answer, in reading order.

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

### `PATCH /morning-brief/checklist/{item_id}`

Marks a checklist item complete or incomplete. This is the only brief state the executive edits directly.

**Request:** `{ "done": true }`

**Response 200:** the updated checklist item. **404** if the item does not exist.

---

## Inbox

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

**Response 200:** a cited report, never a chat message.

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

Triggers a manual read and appends a `running` entry to the audit trail. Returns the full `GET /integrations` payload so the caller gets both the new connection state and the new history entry.

- **404** — unknown integration
- **409** — the integration is not connected yet

---

## Settings

### `GET /settings`

Returns `profile`, `preferences`, `notifications`, `security`, `theme` and `connectedAccounts`.

```json
{
  "profile": {
    "fullName": "Lydia Reyes",
    "role": "Founder & CEO",
    "company": "Arcadia Systems",
    "email": "lydia@arcadiasystems.com",
    "phone": "+30 210 555 0148",
    "timezone": "Europe/Athens (GMT+3)",
    "avatar": "LR"
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
