"""Shared scaffolding for `backend/scripts/seed_*.py`.

Every seed script that writes rows scoped to a user needs the same demo
user (matching `mock_data.USER`) and the same idempotent "skip what's
already there, otherwise insert" loop. Extracted here so each seed script
only defines its own data and its own idempotency key — everything else
(the demo user, the insert loop, the print statements) is written once.

The demo user itself (`DEMO_USER`, `get_or_create_demo_user`) lives in
`app.services.demo_user` — `MorningBriefService` needs it too at request
time, not just from a CLI seed script, so it is re-exported here rather
than duplicated.

`seed_daily_brief.py` does not use this module: `DailyBrief` has no
`user_id` and is written through `DailyBriefService.create_brief()` rather
than a user-scoped insert loop, so there is nothing here for it to share.
"""

from app.services.demo_user import DEMO_USER, get_or_create_demo_user

__all__ = ["DEMO_USER", "get_or_create_demo_user", "seed_idempotently"]


def seed_idempotently(
    db,
    *,
    model,
    user,
    items: list[dict],
    existing_keys: set,
    key_fn,
    describe_fn=None,
    label: str,
) -> int:
    """Insert `items` (each a dict of model kwargs) for `user`, skipping any
    whose `key_fn(item)` is already in `existing_keys`.

    `existing_keys` is computed by the caller (the query differs per model —
    a single column for `Meeting`/`Email`/`Integration`, a tuple of two for
    `Opportunity`) so this stays agnostic of that shape. `describe_fn`
    formats the "already seeded" message for one item; it defaults to
    `repr(key)` when the key alone is a clear enough description.

    Commits once at the end and returns the number of rows actually
    created, matching the behaviour every seed script had before this was
    extracted.
    """
    describe_fn = describe_fn or (lambda item: repr(key_fn(item)))

    created = 0
    for item in items:
        key = key_fn(item)
        if key in existing_keys:
            print(f"Skipping {describe_fn(item)} — already seeded")
            continue

        db.add(model(user_id=user.id, **item))
        created += 1

    db.commit()
    print(f"Seeded {created} {label} for {user.email}")
    return created
