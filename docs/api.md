# Relay API Reference

Base URL: `http://localhost:8000` (development)

All responses are JSON. Interactive docs available at `/docs` (Swagger) and `/redoc`.

---

## Health

### `GET /health`

Returns server health status.

**Response 200:**

```json
{
  "status": "healthy"
}
```

---

## Overview

### `GET /overview`

Returns the executive dashboard payload: user profile, AI summary, KPIs, recommendations, meetings, and activity feed.

**Response 200:**

```json
{
  "user": {
    "name": "Lydia",
    "role": "CEO & Founder",
    "company": "Meridian Labs",
    "avatar": "L"
  },
  "executiveSummary": {
    "generatedAt": "6:30 AM",
    "summary": "Today is high-stakes...",
    "priorities": [
      {
        "id": "1",
        "text": "Review & respond to Horizon Ventures term sheet",
        "urgency": "critical"
      }
    ]
  },
  "kpis": [
    {
      "id": "inbox",
      "label": "Inbox",
      "value": "12",
      "sublabel": "need attention",
      "change": "+3 since yesterday",
      "trend": "up",
      "icon": "inbox",
      "color": "indigo"
    }
  ],
  "aiRecommendations": [
    {
      "id": "1",
      "title": "Respond to Horizon Ventures first",
      "description": "Their term sheet expires Friday...",
      "action": "Draft response",
      "priority": "high"
    }
  ],
  "meetings": [
    {
      "id": "1",
      "title": "Daily Leadership Standup",
      "time": "9:00 AM",
      "duration": "30 min",
      "attendees": ["Sarah Chen", "Marcus Webb", "Elena Park"],
      "type": "internal",
      "location": "Zoom"
    }
  ],
  "activities": [
    {
      "id": "1",
      "type": "email",
      "title": "David Park replied to term sheet thread",
      "time": "25 min ago",
      "icon": "mail"
    }
  ]
}
```

### `GET /overview/daily-brief`

Returns the full daily executive briefing.

**Response 200:**

```json
{
  "date": "Wednesday, July 15, 2026",
  "greeting": "Here's your executive briefing for today.",
  "sections": {
    "priorities": ["Close Horizon Ventures term sheet negotiation..."],
    "meetings": [
      {
        "time": "9:00 AM",
        "title": "Leadership Standup",
        "note": "Discuss hiring plan delays"
      }
    ],
    "pipeline": [
      {
        "company": "Acme Corp",
        "stage": "Negotiation",
        "value": "$850K",
        "note": "85% probability — close expected this week"
      }
    ],
    "deadlines": [
      {
        "item": "Horizon Ventures term sheet response",
        "due": "Today, 6:00 PM",
        "status": "urgent"
      }
    ],
    "risks": [
      {
        "title": "Acme Corp SLA impasse",
        "description": "Their legal team is pushing for 99.99% uptime SLA...",
        "severity": "high"
      }
    ],
    "suggestedActions": [
      "Send Horizon Ventures a counter-proposal..."
    ]
  }
}
```

---

## Calendar

### `GET /calendar`

Returns today's meeting schedule.

**Response 200:**

```json
{
  "date": "Wednesday, July 15, 2026",
  "meetingCount": 4,
  "meetings": [
    {
      "id": "1",
      "title": "Daily Leadership Standup",
      "time": "9:00 AM",
      "duration": "30 min",
      "attendees": ["Sarah Chen", "Marcus Webb", "Elena Park"],
      "type": "internal",
      "location": "Zoom"
    }
  ]
}
```

---

## Inbox

### `GET /inbox`

Returns AI-classified email categories with executive summaries.

**Response 200:**

```json
{
  "categories": [
    {
      "id": "urgent",
      "label": "Urgent",
      "count": 2,
      "emails": [
        {
          "id": "e1",
          "from": "David Park",
          "subject": "Re: Series B Term Sheet — Final Terms",
          "summary": "Horizon Ventures has sent final terms...",
          "time": "25 min ago",
          "unread": true,
          "actionRequired": true
        }
      ]
    }
  ]
}
```

**Category IDs:** `urgent`, `clients`, `investors`, `finance`, `internal`, `newsletters`

---

## CRM

### `GET /crm`

Returns the sales pipeline with deal cards and computed pipeline total.

**Response 200:**

```json
{
  "opportunities": [
    {
      "id": "1",
      "company": "Acme Corp",
      "logo": "AC",
      "stage": "Negotiation",
      "probability": 85,
      "value": 850000,
      "owner": "Marcus Webb",
      "lastActivity": "2 hours ago",
      "aiSummary": "Deal is at the finish line...",
      "tags": ["Enterprise", "Strategic"]
    }
  ],
  "pipelineTotal": 2105000
}
```

---

## Projects

### `GET /projects`

Returns active initiatives with progress tracking.

**Response 200:**

```json
{
  "projects": [
    {
      "id": "1",
      "name": "Series B Fundraise",
      "status": "On Track",
      "progress": 85,
      "owner": "Lydia",
      "dueDate": "Jul 18"
    }
  ]
}
```

**Status values:** `On Track`, `At Risk`

---

## Research

### `GET /research`

Returns AI-curated business intelligence items.

**Response 200:**

```json
{
  "items": [
    {
      "id": "1",
      "title": "AI Infrastructure Market Landscape 2026",
      "source": "a16z",
      "summary": "Enterprise AI adoption growing 3x YoY...",
      "relevance": "high",
      "date": "Today"
    }
  ]
}
```

**Relevance values:** `high`, `medium`

---

## Assistant

### `GET /assistant`

Returns chat suggestions and conversation history.

**Response 200:**

```json
{
  "suggestions": [
    "What needs my attention today?",
    "Summarize my sales pipeline"
  ],
  "history": [
    {
      "id": "1",
      "role": "assistant",
      "content": "Good morning, Lydia. I'm Relay..."
    }
  ]
}
```

### `POST /assistant/chat`

Send a message to the AI assistant.

**Request body:**

```json
{
  "message": "What needs my attention today?"
}
```

**Response 200:**

```json
{
  "id": "1721012345678",
  "role": "assistant",
  "content": "Based on your calendar, inbox, and pipeline..."
}
```

Known suggestion messages return detailed responses. Unknown messages receive a generic fallback.

---

## Settings

### `GET /settings`

Returns user profile, settings sections, and integration status.

**Response 200:**

```json
{
  "user": {
    "name": "Lydia",
    "role": "CEO & Founder",
    "company": "Meridian Labs",
    "avatar": "L"
  },
  "sections": [
    {
      "title": "Profile",
      "description": "Lydia · CEO & Founder at Meridian Labs"
    },
    {
      "title": "Notifications",
      "description": "Daily brief at 6:30 AM, urgent email alerts, meeting reminders"
    }
  ],
  "integrations": [
    {
      "provider": "Gmail",
      "status": "disconnected",
      "description": "Sync and classify executive emails"
    }
  ]
}
```

**Integration status values:** `connected`, `disconnected`, `error`

---

## Error Responses

Standard FastAPI error format:

```json
{
  "detail": "Error message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (validation error) |
| 404 | Resource not found |
| 422 | Request body validation failed |
| 500 | Internal server error |
