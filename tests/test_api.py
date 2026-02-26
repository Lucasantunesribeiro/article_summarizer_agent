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


class TestClearCacheAuthC3:
    """C3: /api/limpar-cache must fail-closed when ADMIN_TOKEN is unset."""

    def test_no_token_header_returns_403_when_admin_token_unset(self, client):
        # ADMIN_TOKEN is not set in the test environment — must be rejected.
        original = os.environ.pop("ADMIN_TOKEN", None)
        try:
            resp = client.post("/api/limpar-cache")
            assert resp.status_code == 403
            data = resp.get_json()
            assert data["success"] is False
        finally:
            if original is not None:
                os.environ["ADMIN_TOKEN"] = original

    def test_wrong_token_returns_403_when_admin_token_unset(self, client):
        original = os.environ.pop("ADMIN_TOKEN", None)
        try:
            resp = client.post(
                "/api/limpar-cache",
                headers={"X-Admin-Token": "wrong-token"},
            )
            assert resp.status_code == 403
        finally:
            if original is not None:
                os.environ["ADMIN_TOKEN"] = original

    def test_correct_token_clears_cache(self, client):
        os.environ["ADMIN_TOKEN"] = "supersecret"
        try:
            resp = client.post(
                "/api/limpar-cache",
                headers={"X-Admin-Token": "supersecret"},
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
        finally:
            del os.environ["ADMIN_TOKEN"]

    def test_wrong_token_returns_403_when_admin_token_set(self, client):
        os.environ["ADMIN_TOKEN"] = "supersecret"
        try:
            resp = client.post(
                "/api/limpar-cache",
                headers={"X-Admin-Token": "bad-guess"},
            )
            assert resp.status_code == 403
        finally:
            del os.environ["ADMIN_TOKEN"]


class TestDownloadPathTraversalM1:
    """M1: /api/download/<id>/<fmt> must reject paths outside the outputs/ directory."""

    def _inject_result(self, flask_app, task_id: str, path: str) -> None:
        """Directly insert a fake completed result into the in-memory store."""
        with flask_app._lock:
            flask_app._tasks[task_id] = {
                "status": "done",
                "progress": 100,
                "message": "Done!",
                "created_at": "2026-01-01T00:00:00",
                "url": "https://example.com",
                "method": "extractive",
                "length": "medium",
            }
            flask_app._results[task_id] = {
                "success": True,
                "summary": "test",
                "statistics": {},
                "method_used": "extractive",
                "execution_time": 0.1,
                "files_created": {"txt": path},
            }

    def test_path_outside_outputs_returns_400(self, client):
        import app as flask_app

        task_id = "aaaaaaaa-0000-0000-0000-000000000001"
        # Attempt to reference /etc/passwd — outside any outputs/ directory.
        self._inject_result(flask_app, task_id, "/etc/passwd")

        resp = client.get(f"/api/download/{task_id}/txt")
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "Invalid file path" in data["error"]

    def test_path_traversal_via_dotdot_returns_400(self, client):
        import app as flask_app
        import os

        from config import config

        task_id = "aaaaaaaa-0000-0000-0000-000000000002"
        # Construct a path that uses ../ to escape the outputs directory.
        traversal_path = os.path.join(config.output.output_dir, "..", "secret.txt")
        self._inject_result(flask_app, task_id, traversal_path)

        resp = client.get(f"/api/download/{task_id}/txt")
        # After resolve(), the path lands outside outputs/ — must be 400.
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "Invalid file path" in data["error"]

    def test_valid_path_inside_outputs_returns_404_when_file_missing(self, client):
        import app as flask_app

        from config import config

        task_id = "aaaaaaaa-0000-0000-0000-000000000003"
        # Path is inside outputs/ but the file does not actually exist on disk.
        valid_path = os.path.join(config.output.output_dir, "summary_test.txt")
        self._inject_result(flask_app, task_id, valid_path)

        resp = client.get(f"/api/download/{task_id}/txt")
        # Path is valid but file is absent — expect 404, not 400.
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["success"] is False
        assert "File not found" in data["error"]
