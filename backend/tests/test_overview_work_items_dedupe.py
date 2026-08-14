"""Overview work-item Actions / Focus must dedupe by WorkItem.id across buckets."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.models import User
from app.services.overview_service import OverviewService, _dedupe_work_items_by_id


def test_dedupe_work_items_by_id_keeps_first_occurrence():
    shared = uuid.uuid4()
    first = SimpleNamespace(id=shared, title="first")
    second = SimpleNamespace(id=shared, title="second-instance")
    other = SimpleNamespace(id=uuid.uuid4(), title="other")
    out = _dedupe_work_items_by_id([first, second, other])
    assert out == [first, other]


def test_work_items_surface_dedupes_overdue_and_high_priority():
    """Same logical task from separate bucket queries must appear once in Actions + Focus."""
    item_id = uuid.uuid4()
    # Distinct instances simulate separate SQLAlchemy query results.
    overdue_instance = SimpleNamespace(
        id=item_id,
        provider="clickup",
        title="[Email Follow-Up] Contract approval",
        description="",
        status="in progress",
        container_name="Inbox",
        priority="urgent",
        url="https://app.clickup.com/t/1",
        due_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_synced_at=None,
        updated_at=None,
        assignee_name=None,
    )
    high_instance = SimpleNamespace(
        id=item_id,
        provider="clickup",
        title="[Email Follow-Up] Contract approval",
        description="",
        status="in progress",
        container_name="Inbox",
        priority="urgent",
        url="https://app.clickup.com/t/1",
        due_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_synced_at=None,
        updated_at=None,
        assignee_name=None,
    )
    open_instance = SimpleNamespace(
        id=item_id,
        provider="clickup",
        title="[Email Follow-Up] Contract approval",
        description="",
        status="in progress",
        container_name="Inbox",
        priority="urgent",
        url="https://app.clickup.com/t/1",
        due_at=datetime.now(timezone.utc) - timedelta(days=1),
        last_synced_at=None,
        updated_at=None,
        assignee_name=None,
    )

    user = User(
        id=uuid.uuid4(),
        email="overview-dedupe@example.com",
        hashed_password="!",
        name="O",
        full_name="O",
        role="CEO",
        company="T",
        avatar="O",
        timezone="UTC",
        is_active=True,
        preferences={},
    )
    service = OverviewService(MagicMock(), user)

    fake_work = MagicMock()
    fake_work.is_any_connected.return_value = True
    fake_work.overdue.return_value = [overdue_instance]
    fake_work.due_soon.return_value = []
    fake_work.high_priority.return_value = [high_instance]
    fake_work.open_items.return_value = [open_instance]
    fake_work.blocked.return_value = []
    fake_work.connected_providers.return_value = ["clickup"]

    import app.services.overview_service as overview_mod

    original = overview_mod.WorkItemService
    overview_mod.WorkItemService = lambda db: fake_work
    try:
        surface = service._work_items_surface()
    finally:
        overview_mod.WorkItemService = original

    assert surface is not None
    focus_ids = [row["id"] for row in surface["focus"]]
    action_ids = [row["id"] for row in surface["recommendedActions"]]
    assert focus_ids.count(f"work_{item_id}") == 1
    assert action_ids.count(f"act_work_{item_id}") == 1
    assert len(focus_ids) == len(set(focus_ids))
    assert len(action_ids) == len(set(action_ids))
