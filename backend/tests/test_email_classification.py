"""Email classification: promo/newsletter stay out of executive priority surfaces."""

from __future__ import annotations

from app.services.email_classification import (
    classify_email_signal,
    classify_from_gmail_metadata,
    is_executive_priority_email,
    is_meeting_prep_email,
)


def test_promotional_gmail_label_not_priority():
    signal = classify_email_signal(
        subject="Get 50% off something tasty",
        sender={"name": "Deals", "email": "deals@promo.example.com"},
        labels=["CATEGORY_PROMOTIONS"],
        label_ids=["CATEGORY_PROMOTIONS"],
    )
    assert signal == "promotional"
    category, priority, _ = classify_from_gmail_metadata(
        subject="Get 50% off something tasty",
        sender={"name": "Deals", "email": "deals@promo.example.com"},
        labels=["CATEGORY_PROMOTIONS"],
        label_ids=["CATEGORY_PROMOTIONS"],
    )
    assert category == "promotional"
    assert priority == "low"
    assert not is_executive_priority_email(
        {"category": category, "priority": priority, "unread": True}
    )


def test_newsletter_not_executive_action():
    signal = classify_email_signal(
        subject="This week in product",
        sender={"name": "Product Weekly", "email": "newsletter@vendor.com"},
        labels=["CATEGORY_UPDATES"],
        label_ids=["CATEGORY_UPDATES"],
        headers={"list-unsubscribe": "<mailto:unsub@vendor.com>"},
    )
    assert signal in ("newsletter", "operational", "automated")
    assert not is_executive_priority_email(
        {"category": "newsletter", "priority": "low", "unread": True}
    )
    assert not is_meeting_prep_email({"category": "newsletter", "priority": "low"})


def test_real_estate_promo_subject_without_stakeholder_history():
    signal = classify_email_signal(
        subject="INVEST IN NAIROBI REAL ESTATE.",
        sender={"name": "Property Bot", "email": "blast@mailchimp.com"},
        labels=[],
        label_ids=[],
        prior_meaningful=False,
    )
    assert signal in ("promotional", "automated")


def test_stakeholder_email_remains_important():
    signal = classify_email_signal(
        subject="Offer terms for renewal",
        sender={"name": "Alex Client", "email": "alex@globex.com"},
        labels=["IMPORTANT"],
        label_ids=["IMPORTANT"],
        prior_meaningful=True,
    )
    assert signal in ("important", "client_stakeholder")
    assert is_executive_priority_email(
        {"category": "high-priority", "priority": "high", "unread": False}
    )


def test_automated_notification_classified():
    signal = classify_email_signal(
        subject="Your receipt from Stripe",
        sender={"name": "Stripe", "email": "noreply@stripe.com"},
        labels=["CATEGORY_UPDATES"],
        label_ids=["CATEGORY_UPDATES"],
    )
    assert signal in ("automated", "newsletter", "operational")
    assert not is_executive_priority_email(
        {"category": "automated", "priority": "low", "unread": True}
    )


def test_needs_reply_stays_priority():
    assert is_executive_priority_email(
        {"category": "needs-reply", "priority": "medium", "unread": False}
    )
