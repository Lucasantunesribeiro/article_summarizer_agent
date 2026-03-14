"""Tests that verify every URL the React frontend calls exists in the Flask API.

These tests protect against the frontend calling endpoints that don't exist,
which would silently fail as 404s in the browser.
"""

from __future__ import annotations


class TestAuthApiEndpoints:
    """Auth endpoints used by frontend/src/api/auth.ts."""

    def test_login_endpoint_exists(self, client):
        # POST /api/auth/login with bad creds → 401, not 404
        response = client.post("/api/auth/login", json={"username": "x", "password": "x"})
        assert response.status_code != 404, "/api/auth/login must exist"

    def test_logout_endpoint_exists(self, client):
        response = client.post("/api/auth/logout")
        assert response.status_code != 404, "/api/auth/logout must exist"

    def test_me_endpoint_exists(self, client):
        # Without JWT → 401/422, not 404
        response = client.get("/api/auth/me")
        assert response.status_code != 404, "/api/auth/me must exist"

    def test_refresh_endpoint_exists(self, client):
        # Without refresh JWT → 401/422, not 404
        response = client.post("/api/auth/refresh")
        assert response.status_code != 404, "/api/auth/refresh must exist"


class TestCoreApiEndpoints:
    """Core API endpoints used by React frontend pages."""

    def test_sumarizar_endpoint_exists(self, client):
        # POST without body → 400, not 404
        response = client.post("/api/sumarizar", json={})
        assert response.status_code != 404, "POST /api/sumarizar must exist"

    def test_health_endpoint_exists(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_history_endpoint_exists(self, client):
        # GET /api/historico → 200/401, not 404
        response = client.get("/api/historico")
        assert response.status_code != 404, "GET /api/historico must exist"

    def test_estatisticas_endpoint_exists(self, client):
        response = client.get("/api/estatisticas")
        assert response.status_code != 404, "GET /api/estatisticas must exist"

    def test_settings_get_endpoint_exists(self, client):
        response = client.get("/api/settings")
        assert response.status_code != 404, "GET /api/settings must exist"


class TestReactSpaRoutes:
    """Verify that UI routes serve the React SPA (or a 503 if not built)."""

    def test_root_serves_spa_or_503(self, client):
        response = client.get("/")
        assert response.status_code in (200, 503), f"/ returned {response.status_code}"

    def test_historico_serves_spa_or_503(self, client):
        response = client.get("/historico")
        assert response.status_code in (200, 503), f"/historico returned {response.status_code}"

    def test_configuracoes_serves_spa_or_503(self, client):
        response = client.get("/configuracoes")
        assert response.status_code in (200, 503), f"/configuracoes returned {response.status_code}"

    def test_login_serves_spa_or_503(self, client):
        response = client.get("/login")
        assert response.status_code in (200, 503), f"/login returned {response.status_code}"

    def test_unknown_ui_route_serves_spa_or_404(self, client):
        response = client.get("/some/unknown/path")
        # Should serve SPA (200) or indicate not built (503), never error 500
        assert response.status_code in (200, 503, 404)
        assert response.status_code != 500

    def test_api_routes_not_intercepted_by_spa(self, client):
        # API routes must never be caught by the SPA catch-all
        response = client.get("/api/does-not-exist")
        assert response.status_code == 404
        data = response.get_json()
        assert data is not None, "API 404 must return JSON"
        assert data.get("success") is False
