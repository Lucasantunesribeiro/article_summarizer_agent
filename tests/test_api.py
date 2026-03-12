"""Integration tests for the Flask API endpoints."""

from __future__ import annotations

from pathlib import Path

from domain.entities import SummarizationTask, TaskStatus
from modules.rate_limiter import InMemoryRateLimiter


def _completed_task(task_id: str, files_created: dict | None = None) -> SummarizationTask:
    task = SummarizationTask(
        id=task_id,
        url="https://example.com/article",
        method="extractive",
        length="medium",
        status=TaskStatus.DONE,
        progress=100,
        message="Done!",
    )
    task.summary = "This is the test summary."
    task.statistics = {
        "words_original": 100,
        "words_summary": 20,
        "compression_ratio": 0.2,
    }
    task.files_created = files_created or {}
    task.method_used = "extractive"
    task.execution_time = 0.5
    return task


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "ok"


class TestAuthEndpoints:
    def test_login_returns_tokens_for_seeded_admin(self, client):
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "Admin123!"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user"]["role"] == "admin"
        assert data["access_token"]
        assert response.headers.getlist("Set-Cookie")

    def test_login_rejects_invalid_credentials(self, client):
        response = client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )

        assert response.status_code == 401
        assert response.get_json()["success"] is False


class TestSummarisationEndpoint:
    def test_valid_request_returns_task_id(self, client, container):
        response = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com/article"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["task_id"]
        assert container.task_repository.get(data["task_id"]) is not None

    def test_missing_url_returns_400(self, client):
        response = client.post("/api/sumarizar", json={})
        assert response.status_code == 400

    def test_invalid_method_returns_400(self, client):
        response = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com", "method": "stealth"},
        )
        assert response.status_code == 400

    def test_invalid_length_returns_400(self, client):
        response = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com", "length": "huge"},
        )
        assert response.status_code == 400

    def test_no_json_body_returns_400(self, client):
        response = client.post("/api/sumarizar", data="not json")
        assert response.status_code == 400


class TestTaskStatusEndpoint:
    def test_unknown_task_returns_404(self, client):
        response = client.get("/api/tarefa/nonexistent-task-id")
        assert response.status_code == 404

    def test_known_task_returns_200(self, client):
        submit_response = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com"},
        )
        task_id = submit_response.get_json()["task_id"]

        response = client.get(f"/api/tarefa/{task_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["task"]["status"] == "queued"

    def test_polling_rate_limit_is_enforced(self, client, container):
        container.rate_limiters["polling"] = InMemoryRateLimiter(max_requests=1, window_seconds=60)
        submit_response = client.post(
            "/api/sumarizar",
            json={"url": "https://example.com/rate-limit"},
        )
        task_id = submit_response.get_json()["task_id"]

        assert client.get(f"/api/tarefa/{task_id}").status_code == 200
        limited = client.get(f"/api/tarefa/{task_id}")
        assert limited.status_code == 429


class TestStatisticsEndpoint:
    def test_stats_returns_200_with_token(self, client, admin_headers):
        response = client.get("/api/estatisticas", headers=admin_headers)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "stats" in data

    def test_stats_returns_401_without_token(self, client):
        response = client.get("/api/estatisticas")
        assert response.status_code == 401


class TestClearCacheAuthorisation:
    def test_requires_jwt(self, client):
        response = client.post("/api/limpar-cache")
        assert response.status_code == 401

    def test_requires_admin_role(self, client, viewer_headers):
        response = client.post("/api/limpar-cache", headers=viewer_headers)
        assert response.status_code == 403

    def test_admin_can_clear_cache(self, client, admin_headers):
        response = client.post("/api/limpar-cache", headers=admin_headers)

        assert response.status_code == 200
        assert response.get_json()["success"] is True

    def test_admin_rate_limit_is_enforced(self, client, container, admin_headers):
        container.rate_limiters["admin"] = InMemoryRateLimiter(max_requests=1, window_seconds=60)

        assert client.post("/api/limpar-cache", headers=admin_headers).status_code == 200
        limited = client.post("/api/limpar-cache", headers=admin_headers)
        assert limited.status_code == 429


class TestSettingsEndpoints:
    def test_admin_can_update_and_read_settings(self, client, admin_headers):
        update_response = client.put(
            "/api/settings",
            headers=admin_headers,
            json={
                "settings": {
                    "scraping.timeout": 45,
                    "rate_limit.polling.max_requests": 25,
                }
            },
        )
        assert update_response.status_code == 200
        assert update_response.get_json()["settings"]["scraping.timeout"] == 45

        get_response = client.get("/api/settings", headers=admin_headers)
        assert get_response.status_code == 200
        data = get_response.get_json()
        assert data["settings"]["scraping.timeout"] == 45
        assert data["settings"]["rate_limit.polling.max_requests"] == 25

    def test_non_admin_cannot_update_settings(self, client, viewer_headers):
        response = client.put(
            "/api/settings",
            headers=viewer_headers,
            json={"settings": {"scraping.timeout": 10}},
        )
        assert response.status_code == 403


class TestDownloadValidation:
    def test_path_outside_outputs_returns_400(self, client, container, tmp_path):
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("secret", encoding="utf-8")
        task = _completed_task(
            "aaaaaaaa-0000-0000-0000-000000000001",
            files_created={"txt": str(outside_file)},
        )
        container.task_repository.add(task)

        response = client.get(f"/api/download/{task.id}/txt")
        assert response.status_code == 400
        assert "Invalid file path" in response.get_json()["error"]

    def test_valid_path_inside_outputs_returns_404_when_missing(self, client, container):
        from config import config

        file_path = Path(config.output.output_dir) / "missing-summary.txt"
        task = _completed_task(
            "aaaaaaaa-0000-0000-0000-000000000002",
            files_created={"txt": str(file_path)},
        )
        container.task_repository.add(task)

        response = client.get(f"/api/download/{task.id}/txt")
        assert response.status_code == 404
        assert "File not found" in response.get_json()["error"]

    def test_valid_path_inside_outputs_downloads_file(self, client, container):
        from config import config

        output_dir = Path(config.output.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        file_path = output_dir / "summary-test.txt"
        file_path.write_text("summary content", encoding="utf-8")

        task = _completed_task(
            "aaaaaaaa-0000-0000-0000-000000000003",
            files_created={"txt": str(file_path)},
        )
        container.task_repository.add(task)

        response = client.get(f"/api/download/{task.id}/txt")
        assert response.status_code == 200
        assert response.data == b"summary content"


class TestWebRoutes:
    def test_homepage_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_404_on_unknown_route(self, client):
        response = client.get("/this/does/not/exist")
        assert response.status_code == 404
