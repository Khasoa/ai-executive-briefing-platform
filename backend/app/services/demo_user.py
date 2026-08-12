"""The single-tenant "current user" for Briefly demo mode.

There is no mandatory authentication in the portfolio demo (see
`Settings.auth_required`). Unauthenticated requests resolve to this user so
the product behaves exactly as it did before Phase 2.1.

When a Bearer access token is present, routes use that user instead. Future
Google OAuth will attach identities to the same `User` row (password may stay
null); this helper remains the unauthenticated fallback only.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import User
from app.services.demo_data import USER

logger = logging.getLogger("briefly.auth")

# ORM-column shape of `demo_data.USER` — kept here so seed scripts and
# request-time persistence share one identity without duplicating strings.
DEMO_USER = {
    "email": USER["email"],
    "name": USER["name"],
    "full_name": USER["fullName"],
    "role": USER["role"],
    "company": USER["company"],
    "avatar": USER["avatar"],
    "timezone": USER["timezone"],
}

# Stable id used only when PostgreSQL is unreachable so services can still
# recognise the demo tenant and fall back to curated data.
DEMO_USER_FALLBACK_ID = uuid.UUID("aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee")


def is_demo_user(user: User) -> bool:
    return user.email == DEMO_USER["email"]


def public_user_dict(user: User) -> dict:
    """Map an ORM user onto the camelCase dict every page already consumes."""
    return {
        "name": user.name,
        "fullName": user.full_name,
        "role": user.role,
        "company": user.company,
        "email": user.email,
        "avatar": user.avatar,
        "timezone": user.timezone,
    }


def settings_profile_dict(user: User) -> dict:
    """Settings profile shape — phone stays curated until a profile column exists."""
    from app.services import demo_data

    phone = demo_data.SETTINGS_PROFILE["phone"] if is_demo_user(user) else ""
    # Authenticated users edit the stored IANA timezone; demo keeps the labelled string.
    timezone_value = (
        demo_data.SETTINGS_PROFILE["timezone"] if is_demo_user(user) else (user.timezone or "UTC")
    )
    return {
        "fullName": user.full_name,
        "role": user.role,
        "company": user.company,
        "email": user.email,
        "phone": phone,
        "timezone": timezone_value,
        "avatar": user.avatar,
        "hasPassword": bool(user.hashed_password),
    }


def _sync_demo_profile(user: User) -> bool:
    """Keep the demo tenant's public identity aligned with `demo_data.USER`."""
    changed = False
    for field, value in DEMO_USER.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            changed = True
    return changed


def get_or_create_demo_user(db: Session) -> User:
    """Find the demo user by email, or create one matching `demo_data.USER`.

    If PostgreSQL is unreachable, returns an unsaved User with a stable id so
    request handlers can continue in curated-data demo mode.
    """
    settings = get_settings()
    try:
        user = db.query(User).filter(User.email == DEMO_USER["email"]).first()
        if user is None:
            user = User(
                **DEMO_USER,
                hashed_password=hash_password(settings.demo_user_password),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

        changed = _sync_demo_profile(user)
        if user.hashed_password is None:
            user.hashed_password = hash_password(settings.demo_user_password)
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user
    except SQLAlchemyError:
        logger.warning(
            "Could not load demo user from PostgreSQL — using in-memory demo identity",
            exc_info=True,
        )
        try:
            db.rollback()
        except SQLAlchemyError:
            pass
        return User(id=DEMO_USER_FALLBACK_ID, **DEMO_USER, hashed_password=None)
