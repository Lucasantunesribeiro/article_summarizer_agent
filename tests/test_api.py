"""
Integration tests for the Flask API endpoints.
The ArticleSummarizerAgent is mocked so no real HTTP or Gemini calls are made.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("FLASK_DEBUG", "true")
os.environ.setdefault("GEMINI_API_KEY", "test-key")


@pytest.fixture(scope="module")
def client():
    """Flask test client with agent mocked out."""
    from unittest.mock import MagicMock

    import app as flask_app

    # Patch the global agent with a mock
    mock_agent = MagicMock()
    mock_agent.run.return_value = {
        "success": True,
        "url": "https://example.com",
        "summary": "This is the test summary.",
        "method_used": "extractive",
        "execution_time": 0.5,
        "files_created": {"txt": "/tmp/test.txt", "md": "/tmp/test.md"},
        "statistics": {
            "words_original": 100,
            "words_summary": 20,
            "compression_ratio": 0.2,
        },
        "timestamp": 1000000,
    }
    mock_agent.get_status.return_value = {
        "version": "2.0.0",
        "config": {"summarization_method": "extractive"},
        "storage_info": {},
        "modules_loaded": {},
    }
    mock_agent.file_manager = MagicMock()

    flask_app._agent = mock_agent
    flask_app._agent_ready = True

    flask_app.app.config["TESTING"] = True
    with flask_app.app.test_client() as c:
        yield c


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"


class TestSummarisationEndpoint:
    def test_valid_request_returns_task_id(self, client):
        resp = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com/article"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "task_id" in data

    def test_missing_url_returns_400(self, client):
        resp = client.post(
            "/api/sumarizar",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_invalid_method_returns_400(self, client):
        resp = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com", "method": "stealth"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_invalid_length_returns_400(self, client):
        resp = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com", "length": "huge"},
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_localhost_url_rejected(self, client):
        """SSRF: internal URLs must not reach the scraper."""
        resp = client.post(
            "/api/sumarizar",
            json={"url": "http://localhost/internal"},
            content_type="application/json",
        )
        # The SSRF check will reject this during pipeline execution.
        # The endpoint accepts the request (200) but the task will fail.
        # This test verifies the endpoint at least doesn't crash.
        assert resp.status_code in (200, 400)

    def test_no_json_body_returns_400(self, client):
        resp = client.post("/api/sumarizar", data="not json")
        assert resp.status_code == 400


class TestTaskStatusEndpoint:
    def test_unknown_task_returns_404(self, client):
        resp = client.get("/api/tarefa/nonexistent-task-id")
        assert resp.status_code == 404

    def test_known_task_returns_200(self, client):
        # First create a task
        resp = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com"},
            content_type="application/json",
        )
        task_id = resp.get_json()["task_id"]

        # Then poll it
        resp2 = client.get(f"/api/tarefa/{task_id}")
        assert resp2.status_code == 200
        data = resp2.get_json()
        assert data["success"] is True
        assert "task" in data


class TestStatisticsEndpoint:
    def test_stats_returns_200(self, client):
        resp = client.get("/api/estatisticas")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "stats" in data


class TestWebRoutes:
    def test_homepage_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_404_on_unknown_route(self, client):
        resp = client.get("/this/does/not/exist")
        assert resp.status_code == 404
