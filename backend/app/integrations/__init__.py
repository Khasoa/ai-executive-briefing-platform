"""External service integrations.

OAuth identity providers live under `app.integrations.oauth`. Data sync:
`google_calendar.py` and `gmail.py` read Google using tokens from OAuthService.
Generation: `openai.py` (Responses API) is used only via `AIService`.
"""

from app.integrations.oauth import get_oauth_provider, list_oauth_providers

__all__ = ["get_oauth_provider", "list_oauth_providers"]