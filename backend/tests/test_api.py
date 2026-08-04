from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_workspace_returns_shell_payload():
    response = client.get("/workspace")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["name"] == "Lydia"
    assert data["brief"]["generatedLabel"]
    assert set(data["badges"]) >= {"inbox", "meetings", "crm"}


def test_overview_returns_summary_kpis_and_focus():
    response = client.get("/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["executiveSummary"]["priorities"]
    assert data["executiveSummary"]["risks"]
    assert len(data["kpis"]) == 4
    assert len(data["focus"]) == 3


def test_morning_brief_has_every_report_section():
    response = client.get("/morning-brief")
    assert response.status_code == 200
    data = response.json()
    for section in (
        "executiveSummary",
        "topPriorities",
        "criticalRisks",
        "meetings",
        "clientsNeedingAttention",
        "importantEmails",
        "suggestedFocus",
        "recommendedDelegation",
        "actionChecklist",
        "closing",
    ):
        assert data[section], f"{section} is empty"
    assert data["meta"]["sources"]


def test_morning_brief_regenerate_refreshes_metadata():
    response = client.post("/morning-brief/regenerate")
    assert response.status_code == 200
    assert response.json()["meta"]["generatedLabel"] == "just now"


def test_checklist_item_can_be_completed():
    item = client.get("/morning-brief").json()["actionChecklist"][0]

    response = client.patch(
        f"/morning-brief/checklist/{item['id']}",
        json={"done": not item["done"]},
    )
    assert response.status_code == 200
    assert response.json()["done"] is not item["done"]

    client.patch(f"/morning-brief/checklist/{item['id']}", json={"done": item["done"]})


def test_unknown_checklist_item_returns_404():
    response = client.patch(
        "/morning-brief/checklist/does-not-exist",
        json={"done": True},
    )
    assert response.status_code == 404


def test_inbox_categorises_every_email():
    response = client.get("/inbox")
    assert response.status_code == 200
    data = response.json()

    category_ids = {category["id"] for category in data["categories"]}
    assert category_ids == {
        "needs-reply",
        "high-priority",
        "waiting",
        "delegated",
        "informational",
    }
    assert all(email["category"] in category_ids for email in data["emails"])
    assert all(email["aiSummary"] and email["readingTime"] for email in data["emails"])


def test_inbox_category_counts_match_the_emails():
    data = client.get("/inbox").json()
    for category in data["categories"]:
        actual = sum(1 for e in data["emails"] if e["category"] == category["id"])
        assert category["count"] == actual


def test_every_email_carries_a_suggested_response():
    emails = client.get("/inbox").json()["emails"]
    assert all(email["suggestedResponse"] for email in emails)


def test_meeting_detail_carries_preparation_intelligence():
    meetings = client.get("/meetings").json()["meetings"]
    assert meetings

    response = client.get(f"/meetings/{meetings[0]['id']}")
    assert response.status_code == 200
    meeting = response.json()
    for field in ("agenda", "talkingPoints", "recommendedQuestions", "attendees"):
        assert meeting[field]


def test_unknown_meeting_returns_404():
    assert client.get("/meetings/does-not-exist").status_code == 404


def test_crm_only_surfaces_opportunities_with_a_next_action():
    response = client.get("/crm")
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["pipelineValue"] > data["summary"]["weightedValue"]
    assert all(deal["recommendedAction"] for deal in data["opportunities"])


def test_ask_workspace_offers_suggested_questions():
    response = client.get("/ask")
    assert response.status_code == 200
    data = response.json()
    assert data["suggestions"]
    assert data["connectedSources"]


def test_ask_answers_with_a_cited_report():
    response = client.post("/ask", json={"question": "What should I prioritize today?"})
    assert response.status_code == 200
    report = response.json()
    assert report["sections"]
    assert report["citations"]
    assert all(citation["source"] for citation in report["citations"])


def test_ask_rejects_an_empty_question():
    assert client.post("/ask", json={"question": "   "}).status_code == 422


def test_integrations_report_connection_state():
    response = client.get("/integrations")
    assert response.status_code == 200
    data = response.json()
    ids = {integration["id"] for integration in data["integrations"]}
    assert ids == {
        "google-calendar",
        "gmail",
        "notion",
        "gohighlevel",
        "openai",
        "n8n",
    }
    assert data["connectedCount"] <= data["totalCount"]
    assert data["syncHistory"]


def test_sync_records_a_history_entry():
    before = len(client.get("/integrations").json()["syncHistory"])

    response = client.post("/integrations/gmail/sync")
    assert response.status_code == 200
    data = response.json()

    assert len(data["syncHistory"]) == before + 1
    assert data["syncHistory"][0]["integrationId"] == "gmail"
    gmail = next(i for i in data["integrations"] if i["id"] == "gmail")
    assert gmail["status"] == "syncing"


def test_disconnected_integration_cannot_sync():
    assert client.post("/integrations/n8n/sync").status_code == 409


def test_sync_of_unknown_integration_returns_404():
    assert client.post("/integrations/does-not-exist/sync").status_code == 404


def test_settings_returns_every_panel():
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    for panel in (
        "profile",
        "preferences",
        "notifications",
        "security",
        "theme",
        "connectedAccounts",
    ):
        assert data[panel]


def test_preferences_update_is_partial():
    original = client.get("/settings").json()["preferences"]

    response = client.patch("/settings/preferences", json={"tone": "Detailed"})
    assert response.status_code == 200
    updated = response.json()
    assert updated["tone"] == "Detailed"
    assert updated["briefTime"] == original["briefTime"]

    client.patch("/settings/preferences", json={"tone": original["tone"]})


def test_actions_are_never_auto_approved():
    assert client.get("/settings").json()["preferences"]["autoApproveActions"] is False

    response = client.patch("/settings/preferences", json={"autoApproveActions": True})
    assert response.status_code == 200
    assert response.json()["autoApproveActions"] is False


def test_notification_can_be_toggled():
    notification = client.get("/settings").json()["notifications"][0]

    response = client.patch(
        f"/settings/notifications/{notification['id']}",
        json={"enabled": not notification["enabled"]},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] is not notification["enabled"]

    client.patch(
        f"/settings/notifications/{notification['id']}",
        json={"enabled": notification["enabled"]},
    )


def test_unknown_notification_returns_404():
    response = client.patch(
        "/settings/notifications/does-not-exist",
        json={"enabled": True},
    )
    assert response.status_code == 404


def test_api_exposes_no_endpoint_that_acts_on_the_executives_behalf():
    """ADR-002: Briefly recommends. It never sends, moves or accepts."""
    forbidden = ("send", "reply", "schedule", "accept", "delete", "close-deal")
    paths = client.get("/openapi.json").json()["paths"]

    assert not [
        path
        for path, operations in paths.items()
        if any(method in operations for method in ("post", "put", "delete"))
        and any(word in path for word in forbidden)
    ]
