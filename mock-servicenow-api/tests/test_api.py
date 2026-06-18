import os
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_DB_PATH = PROJECT_ROOT / "tests" / "test_servicenow.sqlite"

os.environ["SERVICENOW_DB_PATH"] = str(TEST_DB_PATH)
os.environ["SERVICENOW_RESEED_ON_STARTUP"] = "true"
os.environ["MOCK_URL_BASE"] = "http://localhost:8000"

from app.database import init_database  # noqa: E402
from app.main import create_app  # noqa: E402


def build_client() -> TestClient:
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    init_database(reseed=True)
    return TestClient(create_app())


def test_health_endpoint_reports_seeded_counts():
    with build_client() as client:
        response = client.get("/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["incident_count"] == 32
        assert payload["kb_article_count"] == 8


def test_incidents_endpoint_supports_pagination_and_filters():
    with build_client() as client:
        response = client.get(
            "/incidents",
            params={"page": 1, "page_size": 5, "state": "In Progress", "category": "Database"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["pagination"]["page_size"] == 5
        assert payload["pagination"]["total_items"] >= 1
        assert all(item["state"] == "In Progress" for item in payload["items"])
        assert all(item["category"]["name"] == "Database" for item in payload["items"])


def test_incident_detail_includes_related_domains():
    with build_client() as client:
        response = client.get("/incidents/inc-001")
        assert response.status_code == 200
        payload = response.json()
        assert payload["number"].startswith("INC")
        assert len(payload["work_notes"]) >= 2
        assert len(payload["resolution_notes"]) >= 1
        assert len(payload["related_kb_articles"]) >= 1
        assert len(payload["attachments"]) >= 1
        assert len(payload["images"]) >= 1
        assert len(payload["documents"]) >= 1
        assert len(payload["external_references"]) >= 1
        assert len(payload["change_requests"]) >= 1
        assert len(payload["slas"]) == 2


def test_historical_search_and_follow_up_views():
    with build_client() as client:
        history_response = client.get(
            "/incidents/history/search",
            params={"keyword": "timeout", "category": "Database"},
        )
        assert history_response.status_code == 200
        history_payload = history_response.json()
        assert history_payload["pagination"]["total_items"] >= 1
        assert all(item["state"] in {"Resolved", "Closed"} for item in history_payload["items"])

        follow_up_response = client.get("/incidents/follow-up/open", params={"limit": 6})
        assert follow_up_response.status_code == 200
        follow_up_payload = follow_up_response.json()
        assert len(follow_up_payload) == 6
        assert all(item["follow_up_required"] for item in follow_up_payload)


def test_kb_and_asset_endpoints_return_cleaned_data_and_mock_urls():
    with build_client() as client:
        kb_response = client.get("/kb-articles", params={"keyword": "token"})
        assert kb_response.status_code == 200
        kb_item = kb_response.json()["items"][0]
        assert "<" in kb_item["content_html"]
        assert "<" not in kb_item["content_text"]

        attachment_response = client.get("/attachments", params={"incident_id": "inc-001"})
        assert attachment_response.status_code == 200
        asset = attachment_response.json()["items"][0]
        assert asset["mock_url"].startswith("http://localhost:8000/mock/attachments/")
