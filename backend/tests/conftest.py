"""Shared pytest fixtures.

Keep suite offline against the portfolio database: never call live OpenAI
during API contract tests unless a test explicitly configures a fake client.
"""

from __future__ import annotations

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def _disable_live_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
