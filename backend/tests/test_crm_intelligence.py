"""CRM intelligence signals derived from Opportunity dicts (no fabrication)."""

from datetime import date

from app.services.crm_intelligence import derive_crm_signals


def test_derive_crm_signals_from_synced_fields():
    opps = [
        {
            "id": "ghl:1",
            "company": "Acme",
            "value": 250_000,
            "riskLevel": "high",
            "stage": "Negotiation",
            "closeDate": "Aug 12, 2026",
            "lastInteraction": {"time": "10 days ago", "summary": "No reply"},
            "recommendedAction": "Follow up this week",
            "sources": ["GoHighLevel"],
            "aiSummary": "Stalled negotiation",
        },
        {
            "id": "ghl:2",
            "company": "Beta",
            "value": 20_000,
            "riskLevel": "low",
            "stage": "Qualified",
            "closeDate": "Dec 1, 2026",
            "lastInteraction": {"time": "1 hour ago", "summary": "Call"},
            "recommendedAction": "Wait",
            "sources": ["GoHighLevel"],
        },
    ]
    signals = derive_crm_signals(opps, today=date(2026, 8, 8))
    assert len(signals["dealsAtRisk"]) == 1
    assert signals["dealsAtRisk"][0]["source"] == "GoHighLevel"
    assert signals["staleOpportunities"][0]["company"] == "Acme"
    assert signals["upcomingCloses"][0]["company"] == "Acme"
    assert signals["followUpRequired"]
    assert signals["highValueNeedingAttention"][0]["company"] == "Acme"
