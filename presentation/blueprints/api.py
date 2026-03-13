"""REST API blueprint."""

from __future__ import annotations

import os

from flask import Blueprint, Response, current_app, jsonify, request, send_file
from flask_jwt_extended import jwt_required

from application.commands import (
    ClearCacheCommand,
    RotateJwtSecretCommand,
    SubmitSummarizationCommand,
    UpdateSettingsCommand,
)
from application.queries import (
    GetSettingsQuery,
    GetSystemStatusQuery,
    GetTaskDownloadQuery,
    GetTaskStatisticsQuery,
    GetTaskStatusQuery,
)
from config import config
from presentation.blueprints.helpers import (
    enforce_rate_limit,
    get_authenticated_user,
    get_container,
    get_request_ip,
    is_admin_request,
    validate_download_path,
)

api_bp = Blueprint("api", __name__)


def _validate_url(url: str) -> bool:
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except Exception:
        return False


def _normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        if url.startswith("www."):
            url = url[4:]
        url = "https://" + url
    return url


@api_bp.post("/api/sumarizar")
def api_summarize():
    limited = enforce_rate_limit("submit")
    if limited:
        return limited

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "JSON body required."}), 400

    url = _normalise_url(data.get("url", ""))
    if not url or not _validate_url(url):
        return jsonify({"success": False, "error": f"Invalid URL: {url!r}"}), 400

    method = data.get("method", "extractive").lower()
    if method not in ("extractive", "generative"):
        return jsonify(
            {"success": False, "error": 'method must be "extractive" or "generative".'}
        ), 400

    length = data.get("length", "medium").lower()
    if length not in ("short", "medium", "long"):
        return jsonify(
            {"success": False, "error": 'length must be "short", "medium", or "long".'}
        ), 400

    idempotency_key = request.headers.get("X-Idempotency-Key")

    container = get_container()
    task = container.submit_task_handler.handle(
        SubmitSummarizationCommand(
            url=url,
            method=method,
            length=length,
            client_ip=get_request_ip(),
            idempotency_key=idempotency_key,
        )
    )
    return jsonify({"success": True, "task_id": task.id, "message": "Summarisation started."})


@api_bp.get("/api/tarefa/<task_id>")
def api_task_status(task_id: str):
    limited = enforce_rate_limit("polling")
    if limited:
        return limited

    task = get_container().get_task_status_handler.handle(GetTaskStatusQuery(task_id=task_id))
    if not task:
        return jsonify({"success": False, "error": "Task not found."}), 404
    return jsonify({"success": True, "task": task})


@api_bp.get("/api/download/<task_id>/<fmt>")
def api_download(task_id: str, fmt: str):
    path = get_container().get_task_download_handler.handle(
        GetTaskDownloadQuery(task_id=task_id, fmt=fmt)
    )
    if not path:
        return jsonify({"success": False, "error": "Task not found."}), 404

    resolved = validate_download_path(path)
    if not resolved:
        return jsonify({"success": False, "error": "Invalid file path."}), 400
    if not resolved.exists():
        return jsonify({"success": False, "error": "File not found on server."}), 404

    return send_file(
        str(resolved), as_attachment=True, download_name=f"summary_{task_id[:8]}.{fmt}"
    )


@api_bp.get("/api/status")
def api_status():
    return jsonify(
        {
            "success": True,
            "status": get_container().get_system_status_handler.handle(GetSystemStatusQuery()),
        }
    )


@api_bp.get("/api/estatisticas")
@jwt_required()
def api_statistics():
    return jsonify(
        {
            "success": True,
            "stats": get_container().get_task_statistics_handler.handle(GetTaskStatisticsQuery()),
        }
    )


@api_bp.post("/api/limpar-cache")
@jwt_required()
def api_clear_cache():
    limited = enforce_rate_limit("admin")
    if limited:
        return limited
    if not is_admin_request():
        return jsonify({"success": False, "error": "Unauthorised."}), 403

    user = get_authenticated_user()
    result = get_container().clear_cache_handler.handle(
        ClearCacheCommand(
            actor_user_id=user.id if user else None,
            actor_username=user.username if user else None,
        )
    )
    return jsonify(result)


@api_bp.post("/api/admin/rotate-secret")
@jwt_required()
def api_rotate_secret():
    limited = enforce_rate_limit("admin")
    if limited:
        return limited
    if not is_admin_request():
        return jsonify({"success": False, "error": "Unauthorised."}), 403

    data = request.get_json(silent=True) or {}
    user = get_authenticated_user()
    result = get_container().rotate_jwt_secret_handler.handle(
        RotateJwtSecretCommand(
            actor_user_id=user.id if user else None,
            actor_username=user.username if user else None,
            new_secret=data.get("new_secret"),
            grace_period_seconds=int(data.get("grace_period", 3600)),
        )
    )
    return jsonify(result)


@api_bp.get("/api/settings")
@jwt_required()
def api_get_settings():
    return jsonify(
        {
            "success": True,
            "settings": get_container().get_settings_handler.handle(GetSettingsQuery()),
        }
    )


@api_bp.put("/api/settings")
@jwt_required()
def api_update_settings():
    user = get_authenticated_user()
    if not user or not user.can_manage_system():
        return jsonify({"success": False, "error": "Forbidden."}), 403

    payload = request.get_json(silent=True) or {}
    values = payload.get("settings", {})
    if not isinstance(values, dict):
        return jsonify({"success": False, "error": "settings must be an object."}), 400

    saved = get_container().update_settings_handler.handle(
        UpdateSettingsCommand(
            actor_user_id=user.id,
            actor_username=user.username,
            values=values,
        )
    )
    return jsonify({"success": True, "settings": saved})


@api_bp.post("/api/settings/test")
@jwt_required()
def api_test_settings():
    user = get_authenticated_user()
    if not user or not user.can_manage_system():
        return jsonify({"success": False, "error": "Forbidden."}), 403
    return jsonify(
        {
            "success": True,
            "message": "Configuration validated.",
            "status": get_container().get_system_status_handler.handle(GetSystemStatusQuery()),
        }
    )


_METRICS_TOKEN = os.getenv("METRICS_TOKEN")


@api_bp.get("/metrics")
def metrics():
    if _METRICS_TOKEN:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or auth[7:] != _METRICS_TOKEN:
            return jsonify({"error": "unauthorized"}), 401
    prometheus = current_app.extensions.get("prometheus")  # type: ignore[name-defined]
    if not prometheus:
        return Response("prometheus_client not installed", status=501, mimetype="text/plain")
    return Response(
        prometheus["generate_latest"](prometheus["registry"]),
        mimetype="text/plain; version=0.0.4",
    )


@api_bp.get("/health")
def health():
    checks = {"agent": True}

    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            import redis as redis_lib

            redis_lib.from_url(redis_url).ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False
    else:
        checks["redis"] = None

    try:
        from database import init_db

        init_db()
        checks["db"] = True
    except Exception:
        checks["db"] = False

    status_code = 200 if all(value is not False for value in checks.values()) else 503
    return (
        jsonify(
            {
                "status": "ok" if status_code == 200 else "degraded",
                "checks": checks,
                "gemini_model": config.gemini.model_id,
                "summarization_method": config.summarization.method,
            }
        ),
        status_code,
    )
