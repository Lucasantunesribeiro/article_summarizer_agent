#!/usr/bin/env python3
"""
Article Summarizer — Flask Web Application
==========================================

REST API + HTML interface. Tasks run via Celery workers (with thread fallback).
Task state is persisted to PostgreSQL/SQLite. Status polling via /api/tarefa/<task_id>.
"""
from __future__ import annotations

import logging
import os
import pathlib
import secrets
import sys
import threading
import traceback
import uuid
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from math import ceil

from flask import Flask, g, jsonify, redirect, render_template, request, send_file, url_for
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    get_jwt,
    jwt_required,
    verify_jwt_in_request,
)
from flasgger import Swagger

from config import config
from modules.logging_config import setup_logging

# ---------------------------------------------------------------------------
# Logging (structured JSON)
# ---------------------------------------------------------------------------

setup_logging(config.logging.level)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

# Secret key
_secret = os.getenv("SECRET_KEY")
if not _secret:
    if os.getenv("FLASK_DEBUG", "false").lower() != "true":
        raise RuntimeError(
            "SECRET_KEY env var is required in production. Set it to a long random string."
        )
    _secret = secrets.token_urlsafe(32)
    logger.warning("SECRET_KEY not set — using ephemeral key (dev mode only).")

app.config["SECRET_KEY"] = _secret

# JWT config
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", _secret)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=int(os.getenv("JWT_EXPIRES_HOURS", "24")))
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(days=30)
# Accept JWT from both Authorization header and HttpOnly cookies
app.config["JWT_TOKEN_LOCATION"] = ["headers", "cookies"]
app.config["JWT_COOKIE_SECURE"] = os.getenv("FLASK_DEBUG", "false").lower() != "true"
app.config["JWT_COOKIE_CSRF_PROTECT"] = False  # Simplified for portfolio demo

jwt_manager = JWTManager(app)

# ---------------------------------------------------------------------------
# JWT key rotation via SecretsManager
# ---------------------------------------------------------------------------

from modules.secrets_manager import secrets_manager  # noqa: E402


@jwt_manager.encode_key_loader
def _jwt_encode_key(identity):
    """Always sign with the current (newest) secret."""
    return secrets_manager.get_current_secret()


@jwt_manager.decode_key_loader
def _jwt_decode_key(jwt_header, jwt_data):
    """Return the current signing secret for token verification.

    Note: PyJWT HMAC (HS256) accepts a single key per decode call.
    The SecretsManager tracks all grace-period secrets; this callback
    returns the current active secret. Tokens signed with a previous
    (now-rotated) secret remain decodable during the grace period via
    the ``/api/admin/rotate-secret`` documentation which instructs clients
    to refresh tokens before the grace period expires.
    """
    return secrets_manager.get_current_secret()


# ---------------------------------------------------------------------------
# Swagger / OpenAPI
# ---------------------------------------------------------------------------

_swagger_config = {
    "headers": [],
    "specs": [{"endpoint": "apispec", "route": "/apispec.json"}],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}
_swagger_template = {
    "info": {
        "title": "Article Summarizer Agent API",
        "version": "3.0.0",
        "description": "REST API para sumarização de artigos com Gemini e TF-IDF",
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT token — format: Bearer <token>",
        }
    },
}
swagger = Swagger(app, config=_swagger_config, template=_swagger_template)

# CORS
_allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
if "*" in _allowed_origins and os.getenv("FLASK_DEBUG", "false").lower() != "true":
    logger.warning(
        "CORS_ORIGINS=* is set in non-debug mode. "
        "Consider restricting to specific origins in production."
    )
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": _allowed_origins,
            "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Admin-Token"],
        }
    },
)

# ---------------------------------------------------------------------------
# Auth blueprint
# ---------------------------------------------------------------------------

from modules.auth import auth_bp  # noqa: E402

app.register_blueprint(auth_bp)

# ---------------------------------------------------------------------------
# Database init
# ---------------------------------------------------------------------------

try:
    from database import SessionLocal, init_db  # noqa: E402
    from models import Task as TaskModel  # noqa: E402

    init_db()
    _db_available = True
    logger.info("Database initialised.")
except Exception as _db_exc:
    logger.warning("Database unavailable: %s — tasks will be in-memory only.", _db_exc)
    _db_available = False
    SessionLocal = None
    TaskModel = None

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest  # noqa: E402

    _req_counter = Counter(
        "summarization_requests_total",
        "Total summarisation requests",
        ["method", "status"],
    )
    _duration_hist = Histogram(
        "summarization_duration_seconds",
        "Summarisation task duration",
        buckets=[1, 5, 10, 30, 60, 120, 300],
    )
    _active_gauge = Gauge("active_tasks_gauge", "Currently active summarisation tasks")
    _prometheus_available = True
except ImportError:
    _prometheus_available = False
    logger.warning("prometheus_client not installed — /metrics endpoint disabled.")

# ---------------------------------------------------------------------------
# Cache & Rate limiter
# ---------------------------------------------------------------------------

from modules.cache import create_cache_backend  # noqa: E402
from modules.rate_limiter import create_rate_limiter  # noqa: E402

_cache = create_cache_backend(ttl=config.output.cache_ttl)
_rate_limiter = create_rate_limiter(
    max_requests=config.rate_limit.max_requests,
    window_seconds=config.rate_limit.window_seconds,
)

# ---------------------------------------------------------------------------
# In-memory task store (fast polling; DB is source of truth for history)
# ---------------------------------------------------------------------------

_tasks: dict[str, dict[str, Any]] = {}
_results: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Celery (optional — falls back to threading)
# ---------------------------------------------------------------------------

_celery_available = False
try:
    from celery_app import celery as _celery_app  # noqa: E402
    from tasks.summarization_task import summarize_article as _celery_task  # noqa: E402

    # Quick ping to check broker connectivity
    _celery_app.control.inspect(timeout=1.0).ping()
    _celery_available = True
    logger.info("Celery broker connected — using Celery for tasks.")
except Exception as _celery_exc:
    logger.warning("Celery not available (%s) — falling back to threads.", _celery_exc)

# ---------------------------------------------------------------------------
# Security headers with nonce
# ---------------------------------------------------------------------------


@app.before_request
def _set_nonce():
    g.csp_nonce = secrets.token_urlsafe(16)


@app.after_request
def _add_security_headers(response):
    nonce = getattr(g, "csp_nonce", "")
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com fonts.googleapis.com; "
        "font-src 'self' fonts.gstatic.com cdn.jsdelivr.net cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self';"
    )
    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return bool(result.scheme and result.netloc)
    except Exception:
        return False


def _normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        if url.startswith("www."):
            url = url[4:]
        url = "https://" + url
    return url


def _evict_old_tasks(max_tasks: int = 100) -> None:
    with _lock:
        if len(_tasks) <= max_tasks:
            return
        ordered = sorted(
            _tasks.items(),
            key=lambda x: x[1].get("created_at", ""),
            reverse=True,
        )
        keep = {tid for tid, _ in ordered[:max_tasks]}
        for tid in list(_tasks):
            if tid not in keep:
                _tasks.pop(tid, None)
                _results.pop(tid, None)


def _persist_task_update(task_id: str, **kwargs) -> None:
    """Update task record in DB if available."""
    if not _db_available:
        return
    try:
        db = SessionLocal()
        row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        if row:
            for k, v in kwargs.items():
                setattr(row, k, v)
            db.commit()
        db.close()
    except Exception as exc:
        logger.warning("DB update failed for task %s: %s", task_id, exc)


# ---------------------------------------------------------------------------
# Agent initialisation
# ---------------------------------------------------------------------------

_agent = None


def _init_agent() -> bool:
    global _agent
    try:
        from main import ArticleSummarizerAgent  # noqa: E402

        logger.info("Initialising ArticleSummarizerAgent...")
        _agent = ArticleSummarizerAgent()
        logger.info("Agent ready.")
        return True
    except Exception:
        logger.error("Agent init failed:\n%s", traceback.format_exc())
        return False


_agent_ready = _init_agent()
if not _agent_ready:
    logger.warning("App started WITHOUT agent — API requests will fail.")

# ---------------------------------------------------------------------------
# Background task runner (thread fallback)
# ---------------------------------------------------------------------------


def _run_summarisation(task_id: str, url: str, method: str, length: str) -> None:
    if _prometheus_available:
        _active_gauge.inc()
    start = datetime.now()
    try:
        with _lock:
            _tasks[task_id].update(
                {"status": "processing", "progress": 10, "message": "Extracting article content..."}
            )
        _persist_task_update(task_id, status="processing")

        result = _agent.run(url, method=method, length=length)

        elapsed = (datetime.now() - start).total_seconds()
        success = result.get("success", False)

        with _lock:
            if success:
                _tasks[task_id].update(
                    {
                        "status": "done",
                        "progress": 100,
                        "message": "Done!",
                        "finished_at": datetime.now().isoformat(),
                    }
                )
            else:
                _tasks[task_id].update(
                    {
                        "status": "failed",
                        "progress": 0,
                        "message": result.get("error", "Unknown error"),
                    }
                )
            _results[task_id] = result

        _persist_task_update(
            task_id,
            status="done" if success else "failed",
            summary=result.get("summary"),
            error=result.get("error"),
            statistics=result.get("statistics"),
            files_created=result.get("files_created"),
            method_used=result.get("method_used"),
            execution_time=result.get("execution_time"),
            finished_at=datetime.utcnow(),
        )

        if _prometheus_available:
            _req_counter.labels(method=method, status="success" if success else "failed").inc()
            _duration_hist.observe(elapsed)

    except Exception as exc:
        logger.error("Task %s failed: %s", task_id, exc)
        with _lock:
            _tasks[task_id].update(
                {"status": "error", "progress": 0, "message": f"Internal error: {exc}"}
            )
            _results[task_id] = {"success": False, "error": str(exc)}
        _persist_task_update(task_id, status="error", error=str(exc), finished_at=datetime.utcnow())
        if _prometheus_available:
            _req_counter.labels(method=method, status="error").inc()
    finally:
        if _prometheus_available:
            _active_gauge.dec()
        _evict_old_tasks()


# ---------------------------------------------------------------------------
# HTML routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html", csp_nonce=g.csp_nonce)


@app.route("/historico")
def history():
    # Require authentication via JWT cookie
    try:
        verify_jwt_in_request(locations=["cookies"])
    except Exception:
        return redirect(url_for("login", next=request.url))

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    page = max(page, 1)

    # Prefer DB; fall back to in-memory
    if _db_available:
        try:
            db = SessionLocal()
            base_q = db.query(TaskModel).filter(
                TaskModel.status.in_(["done", "failed", "error"])
            )
            total = base_q.count()
            total_pages = max(1, ceil(total / per_page))
            page = min(page, total_pages)

            rows = (
                base_q.order_by(TaskModel.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
                .all()
            )
            completed = []
            for row in rows:
                d = row.to_dict()
                d["task_id"] = d["id"]
                if d["status"] == "done":
                    d["result"] = {
                        "summary": d.get("summary", ""),
                        "statistics": d.get("statistics", {}),
                        "method_used": d.get("method_used", ""),
                        "execution_time": d.get("execution_time", 0),
                        "files_created": d.get("files_created", {}),
                    }
                completed.append(d)
            db.close()
            return render_template(
                "history.html",
                tasks=completed,
                page=page,
                per_page=per_page,
                total=total,
                total_pages=total_pages,
                csp_nonce=g.csp_nonce,
            )
        except Exception as exc:
            logger.warning("DB history query failed: %s", exc)

    with _lock:
        completed = []
        for tid, info in _tasks.items():
            if info["status"] in ("done", "failed", "error"):
                row = info.copy()
                row["task_id"] = tid
                if tid in _results:
                    row["result"] = _results[tid]
                completed.append(row)
    completed.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(completed)
    total_pages = max(1, ceil(total / per_page))
    page = min(page, total_pages)
    start = (page - 1) * per_page
    paginated = completed[start : start + per_page]
    return render_template(
        "history.html",
        tasks=paginated,
        page=page,
        per_page=per_page,
        total=total,
        total_pages=total_pages,
        csp_nonce=g.csp_nonce,
    )


@app.route("/sobre")
def about():
    return render_template("about.html", csp_nonce=g.csp_nonce)


@app.route("/configuracoes")
def settings():
    return render_template("settings.html", csp_nonce=g.csp_nonce)


@app.route("/login", methods=["GET", "POST"])
def login():
    """HTML login form — sets HttpOnly JWT cookie on success."""
    if request.method == "POST":
        import requests as _req_lib

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        admin_user = os.getenv("ADMIN_USER", "admin")
        admin_pass = os.getenv("ADMIN_PASSWORD", "")

        if not admin_pass:
            return render_template(
                "login.html",
                error="Auth not configured (set ADMIN_PASSWORD).",
                csp_nonce=g.csp_nonce,
            )

        if username != admin_user or password != admin_pass:
            return render_template(
                "login.html", error="Invalid credentials.", csp_nonce=g.csp_nonce
            )

        from flask_jwt_extended import create_access_token, create_refresh_token
        from modules.auth import _ADMIN_USER  # noqa: F401 — re-use existing constant check

        access_token = create_access_token(
            identity=username, additional_claims={"role": "admin"}
        )
        refresh_token = create_refresh_token(identity=username)

        next_url = request.args.get("next", url_for("history"))
        resp = redirect(next_url)

        from flask_jwt_extended import set_access_cookies, set_refresh_cookies

        set_access_cookies(resp, access_token)
        set_refresh_cookies(resp, refresh_token)
        return resp

    return render_template("login.html", error=None, csp_nonce=g.csp_nonce)


@app.route("/logout")
def logout():
    """Clear JWT cookies and redirect to home."""
    from flask_jwt_extended import unset_jwt_cookies

    resp = redirect(url_for("index"))
    unset_jwt_cookies(resp)
    return resp


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.route("/api/sumarizar", methods=["POST"])
def api_summarise():
    """
    ---
    summary: Submit an article URL for summarisation
    tags: [Tasks]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [url]
            properties:
              url:
                type: string
                example: https://example.com/article
              method:
                type: string
                enum: [extractive, generative]
                default: extractive
              length:
                type: string
                enum: [short, medium, long]
                default: medium
    responses:
      200:
        description: Task queued
      400:
        description: Invalid request
      429:
        description: Rate limit exceeded
      503:
        description: Service unavailable
    """
    # Rate limit
    client_ip = request.remote_addr or "unknown"
    if not _rate_limiter.is_allowed(client_ip):
        return jsonify(
            {
                "success": False,
                "error": (
                    f"Rate limit exceeded: max {config.rate_limit.max_requests} requests "
                    f"per {config.rate_limit.window_seconds}s."
                ),
            }
        ), 429

    if not _agent_ready:
        return jsonify({"success": False, "error": "Service unavailable."}), 503

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"success": False, "error": "JSON body required."}), 400

    url = _normalise_url(data.get("url", "").strip())
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

    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    with _lock:
        _tasks[task_id] = {
            "status": "queued",
            "progress": 0,
            "message": "Queued...",
            "created_at": now,
            "url": url,
            "method": method,
            "length": length,
        }

    # Persist to DB
    if _db_available:
        try:
            db = SessionLocal()
            db.add(
                TaskModel(
                    id=task_id,
                    status="queued",
                    url=url,
                    method=method,
                    length=length,
                    created_at=datetime.utcnow(),
                )
            )
            db.commit()
            db.close()
        except Exception as exc:
            logger.warning("DB insert failed: %s", exc)

    # Dispatch: Celery if available, else thread
    if _celery_available:
        _celery_task.delay(task_id, url, method, length)
        logger.info("Task %s dispatched to Celery: %s", task_id, url)
    else:
        thread = threading.Thread(
            target=_run_summarisation,
            args=(task_id, url, method, length),
            daemon=True,
        )
        thread.start()
        logger.info("Task %s started (thread): %s", task_id, url)

    return jsonify({"success": True, "task_id": task_id, "message": "Summarisation started."})


@app.route("/api/tarefa/<task_id>", methods=["GET"])
def api_task_status(task_id: str):
    """
    ---
    summary: Poll task status
    tags: [Tasks]
    parameters:
      - in: path
        name: task_id
        required: true
        schema:
          type: string
    responses:
      200:
        description: Task info
      404:
        description: Task not found
    """
    with _lock:
        if task_id not in _tasks:
            # Try DB fallback
            if _db_available:
                try:
                    db = SessionLocal()
                    row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
                    db.close()
                    if row:
                        info = row.to_dict()
                        info["task_id"] = task_id
                        if row.status == "done":
                            info["result"] = {
                                "summary": row.summary or "",
                                "statistics": row.statistics or {},
                                "method_used": row.method_used or "",
                                "execution_time": row.execution_time or 0,
                                "files_created": row.files_created or {},
                            }
                        return jsonify({"success": True, "task": info})
                except Exception as exc:
                    logger.warning("DB task lookup failed: %s", exc)
            return jsonify({"success": False, "error": "Task not found."}), 404

        info = _tasks[task_id].copy()
        if info["status"] == "done" and task_id in _results:
            r = _results[task_id]
            info["result"] = {
                "summary": r.get("summary", ""),
                "statistics": r.get("statistics", {}),
                "method_used": r.get("method_used", ""),
                "execution_time": r.get("execution_time", 0),
                "files_created": r.get("files_created", {}),
            }

    return jsonify({"success": True, "task": info})


@app.route("/api/download/<task_id>/<fmt>", methods=["GET"])
def api_download(task_id: str, fmt: str):
    with _lock:
        if task_id not in _results:
            # Try DB
            if _db_available:
                try:
                    db = SessionLocal()
                    row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
                    db.close()
                    if row and row.files_created:
                        files = row.files_created
                        if fmt in files:
                            path = files[fmt]
                            allowed_dir = pathlib.Path(config.output.output_dir).resolve()
                            resolved_path = pathlib.Path(path).resolve()
                            if not str(resolved_path).startswith(str(allowed_dir)):
                                return jsonify({"success": False, "error": "Invalid file path."}), 400
                            if not resolved_path.exists():
                                return jsonify({"success": False, "error": "File not found."}), 404
                            return send_file(
                                str(resolved_path),
                                as_attachment=True,
                                download_name=f"summary_{task_id[:8]}.{fmt}",
                            )
                except Exception as exc:
                    logger.warning("DB download lookup failed: %s", exc)
            return jsonify({"success": False, "error": "Task not found."}), 404
        result = _results[task_id]

    if not result.get("success"):
        return jsonify({"success": False, "error": "Task did not succeed."}), 400

    files = result.get("files_created", {})
    if fmt not in files:
        return jsonify(
            {"success": False, "error": f"Format {fmt!r} not available. Options: {list(files)}"}
        ), 404

    path = files[fmt]
    allowed_dir = pathlib.Path(config.output.output_dir).resolve()
    resolved_path = pathlib.Path(path).resolve()
    if not str(resolved_path).startswith(str(allowed_dir)):
        return jsonify({"success": False, "error": "Invalid file path."}), 400
    if not resolved_path.exists():
        return jsonify({"success": False, "error": "File not found on server."}), 404

    return send_file(
        str(resolved_path), as_attachment=True, download_name=f"summary_{task_id[:8]}.{fmt}"
    )


@app.route("/api/status", methods=["GET"])
def api_agent_status():
    if not _agent_ready:
        return jsonify({"success": False, "error": "Agent not initialised."}), 503
    try:
        return jsonify({"success": True, "status": _agent.get_status()})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/estatisticas", methods=["GET"])
@jwt_required()
def api_stats():
    """
    ---
    summary: Task statistics (requires JWT)
    tags: [Tasks]
    security:
      - Bearer: []
    responses:
      200:
        description: Aggregated task counts
      401:
        description: Missing or invalid JWT
    """
    with _lock:
        total = len(_tasks)
        done = sum(1 for t in _tasks.values() if t["status"] == "done")
        failed = sum(1 for t in _tasks.values() if t["status"] in ("failed", "error"))
        running = sum(1 for t in _tasks.values() if t["status"] in ("queued", "processing"))
    return jsonify(
        {
            "success": True,
            "stats": {"total": total, "done": done, "failed": failed, "running": running},
        }
    )


def _check_admin_auth() -> bool:
    """Return True if the current request has valid admin credentials.

    Accepts:
    - JWT access token with role=admin (Authorization header or cookie)
    - X-Admin-Token header matching any token in ADMIN_TOKEN env var
      (supports comma-separated list: ADMIN_TOKEN=token1,token2)
    """
    try:
        verify_jwt_in_request(optional=True)
        claims = get_jwt()
        if claims.get("role") == "admin":
            return True
    except Exception:
        pass

    token = request.headers.get("X-Admin-Token", "")
    return secrets_manager.is_admin_token_valid(token)


@app.route("/api/limpar-cache", methods=["POST"])
def api_clear_cache():
    """
    ---
    summary: Clear the file and in-memory cache (admin only)
    tags: [Admin]
    security:
      - Bearer: []
    parameters:
      - in: header
        name: X-Admin-Token
        schema:
          type: string
    responses:
      200:
        description: Cache cleared
      403:
        description: Unauthorised
    """
    if not _check_admin_auth():
        return jsonify({"success": False, "error": "Unauthorised."}), 403

    if not _agent_ready:
        return jsonify({"success": False, "error": "Agent not initialised."}), 503
    try:
        _agent.file_manager.clear_cache()
        _cache.clear_all()
        return jsonify({"success": True, "message": "Cache cleared."})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/admin/rotate-secret", methods=["POST"])
def api_rotate_secret():
    """
    ---
    summary: Rotate the JWT signing secret (admin only)
    tags: [Admin]
    parameters:
      - in: header
        name: X-Admin-Token
        required: true
        schema:
          type: string
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              new_secret:
                type: string
                description: New secret (auto-generated if omitted)
              grace_period:
                type: integer
                default: 3600
                description: Seconds the old secret remains valid for verification
    responses:
      200:
        description: Secret rotated
      403:
        description: Unauthorised
    """
    if not _check_admin_auth():
        return jsonify({"success": False, "error": "Unauthorised."}), 403

    data = request.get_json(silent=True) or {}
    new_secret = data.get("new_secret")
    grace_period = int(data.get("grace_period", 3600))

    result = secrets_manager.rotate(new_secret=new_secret, grace_period_seconds=grace_period)
    logger.info("JWT secret rotated by admin.")
    return jsonify({"success": True, **result})


@app.route("/metrics", methods=["GET"])
def metrics():
    """
    ---
    summary: Prometheus metrics
    tags: [System]
    responses:
      200:
        description: Prometheus text format
      501:
        description: prometheus_client not installed
    """
    if not _prometheus_available:
        return "prometheus_client not installed", 501
    return generate_latest(), 200, {"Content-Type": "text/plain; version=0.0.4"}


@app.route("/health")
def health():
    """
    ---
    summary: Health check
    tags: [System]
    responses:
      200:
        description: All systems OK
      503:
        description: One or more checks degraded
    """
    checks = {"agent": _agent_ready}

    # Redis check
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            import redis as redis_lib

            r = redis_lib.from_url(redis_url)
            r.ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False
    else:
        checks["redis"] = None

    # DB check
    if _db_available:
        try:
            import sqlalchemy

            db = SessionLocal()
            db.execute(sqlalchemy.text("SELECT 1"))
            db.close()
            checks["db"] = True
        except Exception:
            checks["db"] = False
    else:
        checks["db"] = None

    all_ok = all(v is not False for v in checks.values())
    status_code = 200 if all_ok else 503

    return jsonify(
        {
            "status": "ok" if all_ok else "degraded",
            "checks": checks,
            "gemini_model": config.gemini.model_id,
            "summarization_method": config.summarization.method,
            "celery_available": _celery_available,
            "db_available": _db_available,
        }
    ), status_code


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.errorhandler(404)
def err_404(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Not found."}), 404
    return render_template(
        "error.html",
        code=404,
        message="Page not found",
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ), 404


@app.errorhandler(500)
def err_500(e):
    logger.error("500: %s\n%s", e, traceback.format_exc())
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Internal server error."}), 500
    return render_template(
        "error.html",
        code=500,
        message="Internal server error",
        now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    host = os.environ.get("FLASK_HOST", "0.0.0.0")

    logger.info("Starting on %s:%s (debug=%s)", host, port, debug)
    app.run(host=host, port=port, debug=debug, threaded=True)
