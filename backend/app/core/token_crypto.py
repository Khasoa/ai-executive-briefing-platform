"""Encrypt OAuth provider tokens at rest (Fernet over SECRET_KEY)."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings, get_settings


def _fernet(settings: Settings | None = None) -> Fernet:
    settings = settings or get_settings()
    digest = hashlib.sha256(settings.secret_key.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str, settings: Settings | None = None) -> str:
    return _fernet(settings).encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str, settings: Settings | None = None) -> str:
    try:
        return _fernet(settings).decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Unable to decrypt secret") from exc
