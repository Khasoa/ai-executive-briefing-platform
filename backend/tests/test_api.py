from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_overview_endpoint():
    response = client.get("/overview")
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "executiveSummary" in data
    assert data["user"]["name"] == "Lydia"


def test_calendar_endpoint():
    response = client.get("/calendar")
    assert response.status_code == 200
    data = response.json()
    assert data["meetingCount"] == 4
    assert len(data["meetings"]) == 4


def test_inbox_endpoint():
    response = client.get("/inbox")
    assert response.status_code == 200
    assert len(response.json()["categories"]) == 6


def test_crm_endpoint():
    response = client.get("/crm")
    assert response.status_code == 200
    data = response.json()
    assert len(data["opportunities"]) == 6
    assert data["pipelineTotal"] > 0


def test_projects_endpoint():
    response = client.get("/projects")
    assert response.status_code == 200
    assert len(response.json()["projects"]) == 7


def test_research_endpoint():
    response = client.get("/research")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 4


def test_assistant_endpoint():
    response = client.get("/assistant")
    assert response.status_code == 200
    data = response.json()
    assert len(data["suggestions"]) == 5
    assert len(data["history"]) >= 1


def test_assistant_chat():
    response = client.post(
        "/assistant/chat",
        json={"message": "What needs my attention today?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "assistant"
    assert "Horizon Ventures" in data["content"]


def test_settings_endpoint():
    response = client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["company"] == "Meridian Labs"
    assert len(data["integrations"]) == 7
