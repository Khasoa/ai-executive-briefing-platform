"""Canonical supported-integration catalog for the Integrations page.

Connection credentials and sync state always come from the authenticated
user's `integrations` rows. This module only defines which providers exist
and their disconnected display metadata — never another user's data.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# Frontend-facing ids (stable API contract). Google OAuth stores provider="google";
# calendar + gmail cards both derive connection state from that row.
SUPPORTED_INTEGRATIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "google-calendar",
        "provider_keys": ("google-calendar", "google"),
        "name": "Google Calendar",
        "category": "Calendar",
        "description": "Meetings, attendees and scheduling context for meeting intelligence.",
        "scopes": ["calendar.readonly", "calendar.events.readonly"],
        "metrics": [
            {"label": "Meetings today", "value": "—"},
            {"label": "Calendars", "value": "—"},
        ],
        "poweredBy": "Google Workspace API",
        "auth": "oauth",
        "oauthProvider": "google",
    },
    {
        "id": "gmail",
        "provider_keys": ("gmail", "google"),
        "name": "Gmail",
        "category": "Email",
        "description": "Thread summarisation, prioritisation and suggested responses.",
        "scopes": ["gmail.readonly", "gmail.metadata"],
        "metrics": [
            {"label": "Threads indexed", "value": "—"},
            {"label": "Needs reply", "value": "—"},
        ],
        "poweredBy": "Google Workspace API",
        "auth": "oauth",
        "oauthProvider": "google",
    },
    {
        "id": "notion",
        "provider_keys": ("notion",),
        "name": "Notion",
        "category": "Knowledge",
        "description": "Plans, metrics and documents that give the brief its internal context.",
        "scopes": ["read_content", "read_user"],
        "metrics": [
            {"label": "Pages indexed", "value": "—"},
            {"label": "Databases", "value": "—"},
        ],
        "poweredBy": "Notion API",
        "auth": "oauth",
        "oauthProvider": "notion",
    },
    {
        "id": "gohighlevel",
        "provider_keys": ("gohighlevel", "ghl"),
        "name": "GoHighLevel",
        "category": "CRM",
        "description": "Opportunities, stages and interaction history behind pipeline intelligence.",
        "scopes": ["opportunities.readonly", "contacts.readonly"],
        "metrics": [
            {"label": "Opportunities", "value": "—"},
            {"label": "Pipeline", "value": "—"},
        ],
        "poweredBy": "GoHighLevel API",
        "auth": "oauth",
        "oauthProvider": "gohighlevel",
    },
    {
        "id": "monday",
        "provider_keys": ("monday",),
        "name": "monday.com",
        "category": "Work management",
        "description": "Boards, tasks and deadlines that show what needs executive attention.",
        "scopes": ["me:read", "boards:read", "workspaces:read"],
        "metrics": [
            {"label": "Items synced", "value": "—"},
            {"label": "Boards", "value": "—"},
        ],
        "poweredBy": "monday.com API",
        "auth": "oauth",
        "oauthProvider": "monday",
    },
    {
        "id": "clickup",
        "provider_keys": ("clickup",),
        "name": "ClickUp",
        "category": "Work management",
        "description": "Tasks, priorities and owners across authorized ClickUp workspaces.",
        "scopes": ["workspace.read", "tasks.read"],
        "metrics": [
            {"label": "Tasks synced", "value": "—"},
            {"label": "Workspaces", "value": "—"},
        ],
        "poweredBy": "ClickUp API",
        "auth": "oauth",
        "oauthProvider": "clickup",
    },
    {
        "id": "openai",
        "provider_keys": ("openai",),
        "name": "OpenAI",
        "category": "Intelligence",
        "description": "Summarisation, prioritisation and drafting for every generated brief.",
        "scopes": ["responses.write"],
        "metrics": [
            {"label": "Model", "value": "—"},
            {"label": "Briefs generated", "value": "—"},
        ],
        "poweredBy": "OpenAI Platform",
        "auth": "api_key",
        "oauthProvider": None,
    },
    {
        "id": "n8n",
        "provider_keys": ("n8n",),
        "name": "n8n",
        "category": "Automation",
        "description": "Scheduled brief generation and downstream workflow triggers.",
        "scopes": ["workflow.execute"],
        "metrics": [
            {"label": "Workflows", "value": "—"},
            {"label": "Runs this month", "value": "—"},
        ],
        "poweredBy": "n8n Cloud",
        "auth": "webhook",
        "oauthProvider": None,
    },
)


def catalog_ids() -> set[str]:
    return {entry["id"] for entry in SUPPORTED_INTEGRATIONS}


def auth_type_for(entry: dict[str, Any]) -> str:
    auth = entry.get("auth") or "oauth"
    if auth == "config":
        # Back-compat if any leftover "config" markers remain.
        return "api_key" if entry["id"] == "openai" else "webhook"
    if entry.get("oauthProvider") and entry["id"] in ("google-calendar", "gmail"):
        return "derived"
    return str(auth)


def disconnected_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Public IntegrationSchema-shaped dict with no user credentials or sync state."""
    auth_type = auth_type_for(entry)
    return {
        "id": entry["id"],
        "name": entry["name"],
        "category": entry["category"],
        "description": entry["description"],
        "status": "not-connected",
        "account": None,
        "lastSync": None,
        "lastSyncLabel": "Never",
        "scopes": list(entry["scopes"]),
        "metrics": deepcopy(entry["metrics"]),
        "poweredBy": entry["poweredBy"],
        "authType": auth_type,
        "statusDetail": None,
        "canSync": False,
        "canConnect": auth_type in ("oauth", "derived"),
        "canDisconnect": False,
        "canCheck": auth_type in ("api_key", "webhook"),
    }


def resolve_row_for_entry(
    entry: dict[str, Any],
    rows_by_provider: dict[str, Any],
) -> Any | None:
    """Pick the current user's Integration row that satisfies a catalog entry.

    Google Calendar / Gmail cards are fed by `provider=google` OAuth tokens.
    Prefer a connected oauth source row over a stale alias row (e.g. a leftover
    `google-calendar` mirror while `google` is not-connected).
    """
    keys = entry["provider_keys"]
    candidates = [rows_by_provider[key] for key in keys if key in rows_by_provider]
    if not candidates:
        return None

    active = [row for row in candidates if (row.status or "") in ("connected", "syncing")]
    pool = active or candidates

    oauth_provider = entry.get("oauthProvider")
    if oauth_provider:
        for row in pool:
            if row.provider == oauth_provider:
                return row
    return pool[0]
