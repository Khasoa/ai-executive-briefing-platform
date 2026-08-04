"""External service integrations.

Each submodule wraps one provider — Google Calendar, Gmail, OpenAI, GoHighLevel,
Notion, n8n — behind a consistent interface the service layer calls. Scopes are
read-only: Briefly summarises and drafts, it never sends or modifies.

None are implemented yet; services read curated data. See docs/roadmap.md.
"""
