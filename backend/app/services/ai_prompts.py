"""Centralized OpenAI prompt templates and JSON schemas.

All AI capabilities build prompts here so services do not duplicate construction.
"""

from __future__ import annotations

import json
from typing import Any

SYSTEM_EXECUTIVE = (
    "You are Briefly, an AI executive briefing partner. "
    "Recommend; never claim to have sent email, moved deals, or accepted meetings. "
    "Cite only systems present in the provided context. "
    "Return JSON that matches the schema exactly."
)

SOURCE_ENUM = [
    "Gmail",
    "Google Calendar",
    "GoHighLevel",
    "Notion",
    "monday.com",
    "ClickUp",
    "OpenAI",
    "n8n",
]

SEVERITY_ENUM = ["critical", "high", "medium", "low"]


def morning_brief_user_prompt(context: dict[str, Any]) -> str:
    return (
        "Generate today's Morning Brief from this executive context JSON.\n"
        "Distinguish: (A) urgent/action-required, (B) meaningful activity, "
        "(C) routine activity, (D) genuinely no activity.\n"
        "Meeting timing windows matter: only meetingsToday / meetingsNeedingPrepToday are "
        "today preparation items. meetingsThisWeek are upcoming. meetingsLater are planning "
        "context — never treat a monthly/far-future meeting as prepare-today urgency.\n"
        "If nothing is urgent but email/calendar activity exists, write a concise situational "
        "summary — do NOT say there is nothing useful or that no meetings/emails exist.\n"
        "Do not invent email bodies; if summaries are missing, stay at subject/metadata level.\n"
        "Do not invent focus themes like Revenue/Client risk unless evidence appears in context "
        "or explicit preferences.\n"
        "Prefer activityDigest aggregates; treat listed emails/meetings as samples only.\n"
        "When workItems are present, prioritise overdue, high-priority, approaching deadlines, "
        "blocked work, ownership gaps, and meaningful completed work. "
        "Cite monday.com / ClickUp only when those sources appear in context.\n"
        f"CONTEXT:\n{_json(context)}"
    )


def meeting_prep_user_prompt(context: dict[str, Any]) -> str:
    return (
        "Generate meeting preparation for the executive.\n"
        "Include an executive summary, talking points, negotiation strategy, "
        "business risks, questions to ask, and follow-up recommendations.\n"
        f"CONTEXT:\n{_json(context)}"
    )


def email_summary_user_prompt(context: dict[str, Any]) -> str:
    return (
        "Summarise this email for an executive inbox.\n"
        "Provide summary, importance (critical|high|medium|low), action items, "
        "and a short suggested follow-up draft (not sent).\n"
        f"CONTEXT:\n{_json(context)}"
    )


def ask_user_prompt(question: str, context: dict[str, Any]) -> str:
    return (
        "Answer the executive question as a cited report card.\n"
        f"QUESTION: {question}\n"
        f"CONTEXT:\n{_json(context)}"
    )


def weekly_digest_user_prompt(context: dict[str, Any]) -> str:
    return (
        "Generate a cross-system Weekly Intelligence & Next Week Outlook for an executive.\n"
        "Answer two questions: (1) What happened this week? (2) What should they expect next week?\n"
        "Use ONLY sources present in CONTEXT. Leave unsupported arrays empty — never invent rows.\n"
        "Emails: if hasBodySummary is false or dataCoverage.emailNote says the view is limited, "
        "do NOT fabricate body content; say the email view is limited to subject/metadata.\n"
        "week_summary is the narrative for 'what happened'. next_week_outlook is forward-looking.\n"
        "Mark kind=fact for grounded synced data; kind=recommendation only for planning suggestions.\n"
        "Cite Gmail / Google Calendar / GoHighLevel / Notion / monday.com / ClickUp accurately.\n"
        "Prefer factualOutlook lists when grounding upcoming meetings, deadlines, overdue, CRM.\n"
        "Ordinary email volume still counts as weekly activity — use emailActivitySummary.\n"
        "Recurring or later-month meetings are planning context, not urgent prepare-today items.\n"
        "Do NOT dump raw lists. Keep prose tight and executive.\n"
        f"CONTEXT:\n{_json(context)}"
    )


_DIGEST_ITEM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["id", "title", "detail", "source", "emailIds", "kind"],
    "properties": {
        "id": {"type": "string"},
        "title": {"type": "string"},
        "detail": {"type": "string"},
        "source": {"type": "string", "enum": SOURCE_ENUM},
        "emailIds": {"type": "array", "items": {"type": "string"}},
        "kind": {"type": "string", "enum": ["fact", "recommendation"]},
    },
}

_OUTLOOK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "upcoming_meetings",
        "upcoming_deadlines",
        "overdue_work",
        "crm_attention",
        "email_follow_ups",
        "work_items",
        "carry_forward",
        "recommended_priorities",
        "risks_and_watchouts",
        "workload_signals",
    ],
    "properties": {
        "upcoming_meetings": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "upcoming_deadlines": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "overdue_work": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "crm_attention": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "email_follow_ups": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "work_items": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "carry_forward": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "recommended_priorities": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "risks_and_watchouts": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "workload_signals": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
    },
}


WEEKLY_DIGEST_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "week",
        "headline",
        "summary",
        "week_summary",
        "important_conversations",
        "decisions_and_approvals",
        "follow_ups",
        "unresolved_items",
        "notable_activity",
        "carry_into_next_week",
        "next_week_outlook",
        "planning_note",
        "confidence",
        "sources",
    ],
    "properties": {
        "week": {"type": "string"},
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "week_summary": {"type": "string"},
        "important_conversations": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "decisions_and_approvals": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "follow_ups": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "unresolved_items": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "notable_activity": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "carry_into_next_week": {"type": "array", "items": _DIGEST_ITEM_SCHEMA},
        "next_week_outlook": _OUTLOOK_SCHEMA,
        "planning_note": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "sources": {
            "type": "array",
            "items": {"type": "string", "enum": SOURCE_ENUM},
        },
    },
}


MORNING_BRIEF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "headline",
        "executive_summary",
        "confidence",
        "sources",
        "priorities",
        "risks",
        "clients",
        "focus",
        "delegation",
        "closing",
        "checklist",
    ],
    "properties": {
        "headline": {"type": "string"},
        "executive_summary": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "sources": {
            "type": "array",
            "items": {"type": "string", "enum": SOURCE_ENUM},
        },
        "priorities": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "rank", "title", "detail", "urgency", "owner", "source"],
                "properties": {
                    "id": {"type": "string"},
                    "rank": {"type": "integer"},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "urgency": {"type": "string", "enum": SEVERITY_ENUM},
                    "owner": {"type": "string"},
                    "source": {"type": "string", "enum": SOURCE_ENUM},
                },
            },
        },
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "title",
                    "detail",
                    "severity",
                    "impact",
                    "mitigation",
                    "source",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "severity": {"type": "string", "enum": SEVERITY_ENUM},
                    "impact": {"type": "string"},
                    "mitigation": {"type": "string"},
                    "source": {"type": "string", "enum": SOURCE_ENUM},
                },
            },
        },
        "clients": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "company",
                    "stage",
                    "value",
                    "lastContact",
                    "reason",
                    "recommendedAction",
                    "severity",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "company": {"type": "string"},
                    "stage": {"type": "string"},
                    "value": {"type": "string"},
                    "lastContact": {"type": "string"},
                    "reason": {"type": "string"},
                    "recommendedAction": {"type": "string"},
                    "severity": {"type": "string", "enum": SEVERITY_ENUM},
                },
            },
        },
        "focus": {
            "type": "object",
            "additionalProperties": False,
            "required": ["headline", "rationale", "blocks"],
            "properties": {
                "headline": {"type": "string"},
                "rationale": {"type": "string"},
                "blocks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["id", "start", "end", "label", "reason", "kind"],
                        "properties": {
                            "id": {"type": "string"},
                            "start": {"type": "string"},
                            "end": {"type": "string"},
                            "label": {"type": "string"},
                            "reason": {"type": "string"},
                            "kind": {
                                "type": "string",
                                "enum": ["deep-work", "decision", "quick-win", "review"],
                            },
                        },
                    },
                },
            },
        },
        "delegation": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "id",
                    "task",
                    "assignee",
                    "assigneeRole",
                    "reason",
                    "effort",
                ],
                "properties": {
                    "id": {"type": "string"},
                    "task": {"type": "string"},
                    "assignee": {"type": "string"},
                    "assigneeRole": {"type": "string"},
                    "reason": {"type": "string"},
                    "effort": {"type": "string"},
                },
            },
        },
        "closing": {
            "type": "object",
            "additionalProperties": False,
            "required": ["question", "answer", "bullets"],
            "properties": {
                "question": {"type": "string"},
                "answer": {"type": "string"},
                "bullets": {"type": "array", "items": {"type": "string"}},
            },
        },
        "checklist": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["label", "category", "due", "done"],
                "properties": {
                    "label": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["Decision", "Reply", "Delegate", "Review"],
                    },
                    "due": {"type": "string"},
                    "done": {"type": "boolean"},
                },
            },
        },
    },
}


MEETING_PREP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "executiveSummary",
        "talkingPoints",
        "negotiationStrategy",
        "risks",
        "questionsToAsk",
        "followUpRecommendations",
        "prepReason",
    ],
    "properties": {
        "executiveSummary": {"type": "string"},
        "talkingPoints": {"type": "array", "items": {"type": "string"}},
        "negotiationStrategy": {"type": "string"},
        "risks": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "detail", "severity"],
                "properties": {
                    "title": {"type": "string"},
                    "detail": {"type": "string"},
                    "severity": {"type": "string", "enum": SEVERITY_ENUM},
                },
            },
        },
        "questionsToAsk": {"type": "array", "items": {"type": "string"}},
        "followUpRecommendations": {"type": "array", "items": {"type": "string"}},
        "prepReason": {"type": "string"},
    },
}


EMAIL_SUMMARY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "importance", "actionItems", "followUpSuggestion"],
    "properties": {
        "summary": {"type": "string"},
        "importance": {"type": "string", "enum": SEVERITY_ENUM},
        "actionItems": {"type": "array", "items": {"type": "string"}},
        "followUpSuggestion": {"type": "string"},
    },
}


ASK_REPORT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "confidence", "sections", "citations", "followUps"],
    "properties": {
        "summary": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["id", "title", "type", "items", "body"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["ranked", "list", "text", "draft"],
                    },
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["title", "detail", "meta"],
                            "properties": {
                                "title": {"type": "string"},
                                "detail": {"type": ["string", "null"]},
                                "meta": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "body": {"type": ["string", "null"]},
                },
            },
        },
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "detail", "count"],
                "properties": {
                    "source": {"type": "string", "enum": SOURCE_ENUM},
                    "detail": {"type": "string"},
                    "count": {"type": "integer"},
                },
            },
        },
        "followUps": {"type": "array", "items": {"type": "string"}},
    },
}


def _json(value: Any) -> str:
    return json.dumps(value, default=str, ensure_ascii=False, indent=2)
