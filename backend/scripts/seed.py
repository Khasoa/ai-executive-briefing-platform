"""Seed every persistence-backed domain into PostgreSQL.

Usage (from backend/):

    python3 scripts/seed.py

Runs the individual `seed_*.py` scripts in dependency order so an empty
database becomes a complete demo environment in one command. Each step is
idempotent — re-running this entry point is always safe.

Order:
  1. daily_brief      (no user FK)
  2. meetings         (needs demo user)
  3. emails           (needs demo user)
  4. opportunities    (needs demo user)
  5. integrations     (needs demo user)
  6. sync_events      (needs integrations)
  7. morning_brief    (needs demo user; pulls live meetings/emails)
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent

# Match the individual seed scripts: allow `from app...` and `from seed_common`.
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

# (module_name, human label) — dependency order matters.
SEED_STEPS: list[tuple[str, str]] = [
    ("seed_daily_brief", "DailyBrief"),
    ("seed_meetings", "Meetings"),
    ("seed_emails", "Emails"),
    ("seed_opportunities", "Opportunities"),
    ("seed_integrations", "Integrations"),
    ("seed_sync_events", "Sync events"),
    ("seed_morning_brief", "MorningBrief"),
]


def main() -> int:
    print("Seeding Briefly demo data…")
    for module_name, label in SEED_STEPS:
        print(f"\n=== {label} ({module_name}.py) ===")
        module = importlib.import_module(module_name)
        module.seed()
    print("\nDone. All seed steps completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
