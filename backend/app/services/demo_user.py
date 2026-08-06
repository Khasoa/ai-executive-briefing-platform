"""The single-tenant "current user" for Briefly today.

There is no authentication yet (see the roadmap in `backend/README.md`), so
every per-user table (`Meeting`, `Email`, `Opportunity`, `Integration`,
`MorningBrief`) is scoped to one demo user matching `demo_data.USER`. This is
the one place that resolves or creates that user — `MorningBriefService` and
`scripts/seed_common.py` both call this instead of each keeping their own
copy of the demo user's identity.
"""

from sqlalchemy.orm import Session

from app.models import User
from app.services.demo_data import USER

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


def get_or_create_demo_user(db: Session) -> User:
    """Find the demo user by email, or create one matching `demo_data.USER`."""
    user = db.query(User).filter(User.email == DEMO_USER["email"]).first()
    if user:
        return user

    user = User(**DEMO_USER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
