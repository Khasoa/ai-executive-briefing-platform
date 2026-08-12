"""OpenAI Responses API client.

Services never call OpenAI HTTP directly — they go through `AIService`,
which owns failover and caching. This module is the transport + JSON parse.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings, get_settings

logger = logging.getLogger("briefly.openai")

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


class OpenAIError(Exception):
    """Base class for provider failures that should trigger curated failover."""


class OpenAINotConfigured(OpenAIError):
    pass


class OpenAITimeout(OpenAIError):
    pass


class OpenAIRateLimit(OpenAIError):
    pass


class OpenAIUnavailable(OpenAIError):
    pass


class OpenAIBadResponse(OpenAIError):
    pass


class OpenAIClient:
    """Thin Responses API wrapper. No business logic."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.api_key = (self.settings.openai_api_key or "").strip()
        self.model = self.settings.openai_model.strip() or "gpt-4.1-mini"
        self.embed_model = self.settings.openai_embed_model.strip() or "text-embedding-3-small"
        self.timeout = float(self.settings.openai_timeout_seconds)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate_json(
        self,
        *,
        system: str,
        user: str,
        schema_name: str,
        schema: dict[str, Any],
        model: str | None = None,
    ) -> dict[str, Any]:
        """Call Responses API and return parsed JSON object."""
        if not self.is_configured():
            raise OpenAINotConfigured("OPENAI_API_KEY is not set")

        payload = {
            "model": model or self.model,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "schema": schema,
                    "strict": True,
                }
            },
        }
        data = self._post(payload)
        text = _extract_output_text(data)
        if not text:
            raise OpenAIBadResponse("OpenAI response contained no text")
        try:
            import json

            parsed = json.loads(text)
        except (TypeError, ValueError) as exc:
            raise OpenAIBadResponse("OpenAI response was not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise OpenAIBadResponse("OpenAI JSON root must be an object")
        return parsed

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = httpx.post(
                OPENAI_RESPONSES_URL,
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise OpenAITimeout("OpenAI request timed out") from exc
        except httpx.HTTPError as exc:
            raise OpenAIUnavailable("OpenAI provider unreachable") from exc

        if response.status_code == 429:
            raise OpenAIRateLimit("OpenAI rate limit exceeded")
        if response.status_code in (401, 403):
            raise OpenAIUnavailable("OpenAI authentication failed")
        if response.status_code >= 500:
            raise OpenAIUnavailable(f"OpenAI unavailable ({response.status_code})")
        if response.status_code >= 400:
            raise OpenAIBadResponse(f"OpenAI rejected the request ({response.status_code})")

        try:
            return response.json()
        except ValueError as exc:
            raise OpenAIBadResponse("OpenAI returned non-JSON body") from exc


def _extract_output_text(data: dict[str, Any]) -> str:
    """Best-effort extract of assistant text from a Responses API payload."""
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"]

    chunks: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for part in item.get("content") or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") in ("output_text", "text") and part.get("text"):
                chunks.append(str(part["text"]))
    if chunks:
        return "".join(chunks)

    # Legacy-ish fallbacks if the envelope shape drifts.
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        message = (choices[0] or {}).get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""
