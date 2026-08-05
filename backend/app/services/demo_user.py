"""The single-tenant "current user" for Briefly today.

There is no authentication yet (see the roadmap in `backend/README.md`), so
every per-user table (`Meeting`, `Email`, `Opportunity`, `Integration`,
`MorningBrief`) is scoped to one demo user matching `mock_data.USER`. This is
the one place that resolves or creates that user — `MorningBriefService` and
`scripts/seed_common.py` both call this instead of each keeping their own
copy of the demo user's identity.
"""

from sqlalchemy.orm import Session

from app.models import User

DEMO_USER = {
    "email": "lydia@arcadiasystems.com",
    "name": "Lydia",
    "full_name": "Lydia Reyes",
    "role": "Founder & CEO",
    "company": "Arcadia Systems",
    "avatar": "LR",
    "timezone": "Europe/Athens",
}


def get_or_create_demo_user(db: Session) -> User:
    """Find the demo user by email, or create one matching `mock_data.USER`."""
    user = db.query(User).filter(User.email == DEMO_USER["email"]).first()
    if user:
        return user

    user = User(**DEMO_USER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
