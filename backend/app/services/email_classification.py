"""Shared email signal classification for Inbox / Brief / Overview / Digest / Meetings.

Deterministic heuristics based on Gmail labels, sender metadata, and subject patterns.
Never invents body content. Promotional/newsletter mail stays visible in Inbox but
is excluded from executive priority surfaces unless strong stakeholder evidence exists.
"""

from __future__ import annotations

import re
from typing import Any, Literal

EmailSignal = Literal[
    "action_required",
    "important",
    "client_stakeholder",
    "operational",
    "informational",
    "promotional",
    "newsletter",
    "automated",
    "low_priority",
]

# Maps product signal → persisted Email.category (schema-compatible, additive).
SIGNAL_TO_CATEGORY: dict[EmailSignal, str] = {
    "action_required": "needs-reply",
    "important": "high-priority",
    "client_stakeholder": "high-priority",
    "operational": "informational",
    "informational": "informational",
    "promotional": "promotional",
    "newsletter": "newsletter",
    "automated": "automated",
    "low_priority": "informational",
}

EXECUTIVE_PRIORITY_CATEGORIES = frozenset(
    {"needs-reply", "high-priority", "waiting"}
)
NON_PRIORITY_CATEGORIES = frozenset(
    {"promotional", "newsletter", "automated", "informational", "delegated"}
)

_PROMO_SUBJECT = re.compile(
    r"("
    r"\b\d{1,3}%\s*off\b|"
    r"\bsale\b|"
    r"\bdiscount\b|"
    r"\bfree\s+shipping\b|"
    r"\blimited\s+time\b|"
    r"\bdeal(s)?\b|"
    r"\boffer\b|"
    r"\bcoupon\b|"
    r"\binvest\s+in\b|"
    r"\breal\s+estate\b|"
    r"\bnewsletter\b|"
    r"\bunsubscribe\b|"
    r"\bclick\s+here\b|"
    r"\bdon'?t\s+miss\b|"
    r"\blast\s+chance\b|"
    r"\bpromo(tion)?\b"
    r")",
    re.I,
)

_NEWSLETTER_SENDER = re.compile(
    r"(newsletter|news@|noreply|no-reply|donotreply|do-not-reply|mailer-daemon|"
    r"notifications?@|updates?@|marketing@|promo@|hello@mail\.|info@)",
    re.I,
)

_AUTOMATED_SUBJECT = re.compile(
    r"("
    r"\byour\s+(receipt|invoice|statement)\b|"
    r"\bpassword\s+reset\b|"
    r"\bverify\s+your\b|"
    r"\bsecurity\s+alert\b|"
    r"\blogin\s+from\b|"
    r"\bautomatic(ally)?\b|"
    r"\bdo\s+not\s+reply\b"
    r")",
    re.I,
)

_KNOWN_PROMO_DOMAINS = frozenset(
    {
        "mailchimp.com",
        "sendgrid.net",
        "constantcontact.com",
        "klaviyo.com",
        "hubspotemail.net",
        "amazonses.com",
        "mailgun.org",
        "sparkpostmail.com",
        "substack.com",
        "beehiiv.com",
        "convertkit.com",
    }
)


def classify_email_signal(
    *,
    subject: str = "",
    sender: dict[str, Any] | None = None,
    labels: list[str] | None = None,
    label_ids: list[str] | None = None,
    headers: dict[str, str] | None = None,
    existing_category: str | None = None,
    prior_meaningful: bool = False,
) -> EmailSignal:
    """Classify an email into an executive signal using metadata only."""
    labels = labels or []
    label_ids = label_ids or []
    headers = {k.lower(): v for k, v in (headers or {}).items()}
    sender = sender or {}
    subject = subject or ""

    upper_labels = {str(x).upper() for x in labels} | {str(x).upper() for x in label_ids}
    sender_email = (sender.get("email") or "").strip().lower()
    sender_name = (sender.get("name") or "").strip()
    domain = sender_email.split("@")[-1] if "@" in sender_email else ""

    list_unsub = bool(
        headers.get("list-unsubscribe")
        or headers.get("list-id")
        or "List-Unsubscribe" in (headers.get("list-unsubscribe") or "")
    )
    precedence = (headers.get("precedence") or "").lower()
    auto_submitted = (headers.get("auto-submitted") or "").lower()

    # Strong Gmail taxonomy first.
    if "CATEGORY_PROMOTIONS" in upper_labels:
        if prior_meaningful:
            return "client_stakeholder"
        return "promotional"
    if "CATEGORY_UPDATES" in upper_labels and not prior_meaningful:
        # Updates are often automated receipts / platform notices.
        if _AUTOMATED_SUBJECT.search(subject) or _NEWSLETTER_SENDER.search(sender_email):
            return "automated"
        return "newsletter" if list_unsub or _NEWSLETTER_SENDER.search(sender_email) else "operational"
    if "CATEGORY_FORUMS" in upper_labels or "CATEGORY_SOCIAL" in upper_labels:
        return "low_priority"

    if "IMPORTANT" in upper_labels or "STARRED" in upper_labels:
        return "important"

    # Preserve intentional executive categories already set.
    if existing_category in ("needs-reply", "high-priority", "waiting", "delegated"):
        if existing_category == "needs-reply":
            return "action_required"
        if existing_category == "high-priority":
            return "important"
        if existing_category == "waiting":
            return "operational"
        return "operational"

    if prior_meaningful and not (
        "CATEGORY_PROMOTIONS" in upper_labels
        or domain in _KNOWN_PROMO_DOMAINS
    ):
        return "client_stakeholder"

    if (
        precedence in {"bulk", "junk", "list"}
        or auto_submitted not in {"", "no"}
        or domain in _KNOWN_PROMO_DOMAINS
    ):
        if _PROMO_SUBJECT.search(subject) or list_unsub:
            return "promotional"
        return "automated"

    if list_unsub or _NEWSLETTER_SENDER.search(sender_email) or _NEWSLETTER_SENDER.search(
        sender_name
    ):
        if _PROMO_SUBJECT.search(subject):
            return "promotional"
        return "newsletter"

    if _AUTOMATED_SUBJECT.search(subject):
        return "automated"

    if _PROMO_SUBJECT.search(subject) and not prior_meaningful:
        return "promotional"

    return "informational"


def category_from_signal(signal: EmailSignal) -> str:
    return SIGNAL_TO_CATEGORY.get(signal, "informational")


def priority_from_signal(signal: EmailSignal) -> str:
    if signal in ("action_required", "important", "client_stakeholder"):
        return "high"
    if signal in ("promotional", "newsletter", "automated", "low_priority"):
        return "low"
    return "medium"


def is_executive_priority_email(email: dict[str, Any] | None) -> bool:
    """Whether an email belongs on Top Priorities / Focus / prepare-today context."""
    if not email:
        return False
    category = (email.get("category") or "").strip().lower()
    priority = (email.get("priority") or "").strip().lower()
    if category in {"promotional", "newsletter", "automated"}:
        return False
    if priority == "low" and category == "informational":
        return False
    if category in EXECUTIVE_PRIORITY_CATEGORIES:
        return True
    if priority in {"critical", "high"} and category not in NON_PRIORITY_CATEGORIES - {
        "informational"
    }:
        # High priority informational can still surface if not promo-classed.
        if category == "informational" and priority == "high":
            return True
        if category in {"needs-reply", "high-priority", "waiting"}:
            return True
    if email.get("unread") and category in {"needs-reply", "high-priority"}:
        return True
    # Unread alone is not enough — avoids promo unread flooding Focus.
    return False


def is_meeting_prep_email(email: dict[str, Any] | None) -> bool:
    """Related emails shown in meeting prep — exclude promo/newsletter/automated."""
    if not email:
        return False
    category = (email.get("category") or "").strip().lower()
    if category in {"promotional", "newsletter", "automated"}:
        return False
    return True


def classify_from_gmail_metadata(
    *,
    subject: str,
    sender: dict[str, Any],
    labels: list[str],
    label_ids: list[str],
    headers: dict[str, str] | None = None,
    prior_meaningful: bool = False,
) -> tuple[str, str, EmailSignal]:
    """Return (category, priority, signal) for Gmail sync upserts."""
    signal = classify_email_signal(
        subject=subject,
        sender=sender,
        labels=labels,
        label_ids=label_ids,
        headers=headers,
        prior_meaningful=prior_meaningful,
    )
    return category_from_signal(signal), priority_from_signal(signal), signal
