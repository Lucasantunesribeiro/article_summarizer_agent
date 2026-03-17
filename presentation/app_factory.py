"""Flask application factory."""

from __future__ import annotations

import logging
import os
import secrets
import traceback
from datetime import timedelta
from pathlib import Path

from flasgger import Swagger
from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import config
from database import upgrade_schema
from infrastructure.container import build_runtime_container
from modules.logging_config import setup_logging
from modules.tracing import setup_tracing
from presentation.blueprints.api import api_bp
from presentation.blueprints.auth import auth_bp
from presentation.blueprints.web import web_bp


def create_app() -> Flask:
    setup_logging(config.logging.level)
    logger = logging.getLogger(__name__)
    project_root = Path(__file__).resolve().parents[1]

    app = Flask(
        __name__,
        template_folder=str(project_root / "templates"),
        static_folder=str(project_root / "static"),
    )

    # OpenTelemetry must be set up before blueprint registration
    setup_tracing(app)
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        if os.getenv("FLASK_DEBUG", "false").lower() != "true":
            raise RuntimeError("SECRET_KEY env var is required in production.")
        secret_key = secrets.token_urlsafe(32)
        logger.warning("SECRET_KEY not set — using ephemeral key (dev mode only).")

    app.config["SECRET_KEY"] = secret_key
    app.config["JWT_SECRET_KEY"] = secret_key
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=config.auth.jwt_expires_hours)
    app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
    app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
    app.config["JWT_COOKIE_SECURE"] = config.auth.jwt_cookie_secure
    app.config["JWT_COOKIE_CSRF_PROTECT"] = config.auth.jwt_cookie_csrf_protect
    app.config["JWT_COOKIE_SAMESITE"] = "Lax"
    app.config["JWT_CSRF_IN_COOKIES"] = True
    app.config["JWT_CSRF_CHECK_FORM"] = False
    app.config["JWT_ACCESS_CSRF_HEADER_NAME"] = "X-CSRF-TOKEN"
    app.config["JWT_REFRESH_CSRF_HEADER_NAME"] = "X-CSRF-TOKEN"

    swagger = Swagger(
        app,
        config={
            "headers": [],
            "specs": [{"endpoint": "apispec", "route": "/apispec.json"}],
            "static_url_path": "/flasgger_static",
            "swagger_ui": True,
            "specs_route": "/apidocs/",
        },
        template={
            "info": {
                "title": "Article Summarizer Agent API",
                "version": "3.0.0",
                "description": "REST API para sumarização de artigos com Clean Architecture",
            }
        },
    )
    app.extensions["swagger"] = swagger

    allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": [
                    "Content-Type",
                    "Authorization",
                    "X-CSRF-TOKEN",
                    "X-Idempotency-Key",
                ],
            }
        },
    )

    upgrade_schema()
    container = build_runtime_container()
    app.extensions["container"] = container

    jwt = JWTManager(app)

    @jwt.encode_key_loader
    def _jwt_encode_key(identity):
        return container.secrets_manager.get_current_secret()

    @jwt.decode_key_loader
    def _jwt_decode_key(jwt_header, jwt_payload):
        key_id = jwt_header.get("kid")
        return (
            container.secrets_manager.get_secret_for_kid(key_id)
            or container.secrets_manager.get_current_secret()
        )

    @jwt.additional_headers_loader
    def _jwt_additional_headers(identity):
        return {"kid": container.secrets_manager.get_current_key_id()}

    @app.before_request
    def _set_nonce():
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.before_request
    def _set_request_id():
        from uuid import uuid4

        g.request_id = request.headers.get("X-Request-ID") or str(uuid4())

    @app.after_request
    def _add_security_headers(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        try:
            from modules.metrics import HTTP_REQUESTS

            HTTP_REQUESTS.labels(
                method=request.method,
                endpoint=request.endpoint or "unknown",
                status=str(response.status_code),
            ).inc()
        except Exception:
            pass
        return response

    try:
        from prometheus_client import generate_latest

        from modules.metrics import REGISTRY

        app.extensions["prometheus"] = {
            "generate_latest": generate_latest,
            "registry": REGISTRY,
        }
    except ImportError:
        app.extensions["prometheus"] = None

    app.register_blueprint(web_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    @app.errorhandler(404)
    def handle_404(error):
        if request.path.startswith("/api/") or request.path.startswith("/auth/"):
            return jsonify({"success": False, "error": "Not found."}), 404
        # For all other paths, serve the React SPA (React Router handles 404 display)
        from pathlib import Path

        from flask import send_file

        index = Path(app.static_folder) / "dist" / "index.html"
        if index.exists():
            return send_file(str(index)), 200
        return jsonify({"success": False, "error": "Not found."}), 404

    @app.errorhandler(500)
    def handle_500(error):
        logger.error("500: %s\n%s", error, traceback.format_exc())
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "error": "Internal server error."}), 500
        return (
            render_template(
                "error.html",
                code=500,
                message="Internal server error",
                now="",
            ),
            500,
        )

    return app
