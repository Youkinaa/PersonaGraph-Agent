from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["phase"] == "phase_1_task_state"


def test_workspace_pages_render() -> None:
    client = TestClient(app)

    index_response = client.get("/")
    partial_response = client.get("/partials/phase-status")

    assert index_response.status_code == 200
    assert "text/html" in index_response.headers["content-type"]
    assert partial_response.status_code == 200
    assert "text/html" in partial_response.headers["content-type"]
