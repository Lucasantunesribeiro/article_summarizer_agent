#!/usr/bin/env python3
"""
Article Summarizer — Flask Web Application
==========================================

REST API + HTML interface.  Tasks run in background threads; status is
polled via /api/tarefa/<task_id>.

Production note:
  Use Gunicorn with multiple workers in production.
  In-memory task state is lost on restart — swap for Redis/Celery for
  persistent jobs.
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
from collections import defaultdict
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request, send_file
from flask_cors import CORS

from config import config
from main import ArticleSummarizerAgent

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("flask_app.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

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

_allowed_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": _allowed_origins,
            "methods": ["GET", "POST", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    },
)

# ---------------------------------------------------------------------------
# In-memory task store
# ---------------------------------------------------------------------------

_tasks: dict[str, dict[str, Any]] = {}
_results: dict[str, dict[str, Any]] = {}
_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Simple in-memory rate limiter (per-IP, fixed window)
# ---------------------------------------------------------------------------

_rate_windows: dict[str, list] = defaultdict(list)
_rate_lock = threading.Lock()


def _check_rate_limit(ip: str) -> bool:
    """Return True if the request should be allowed, False if rate-limited."""
    now = datetime.now().timestamp()
    window = config.rate_limit.window_seconds
    max_req = config.rate_limit.max_requests

    with _rate_lock:
        timestamps = _rate_windows[ip]
        # Evict old entries
        _rate_windows[ip] = [t for t in timestamps if now - t < window]
        if len(_rate_windows[ip]) >= max_req:
            return False
        _rate_windows[ip].append(now)
        return True


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
    if url.startswith("www."):
        url = url[4:]
    if not url.startswith(("http://", "https://")):
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


# ---------------------------------------------------------------------------
# Agent initialisation
# ---------------------------------------------------------------------------

_agent: ArticleSummarizerAgent | None = None


def _init_agent() -> bool:
    global _agent
    try:
        logger.info("Initialising ArticleSummarizerAgent…")
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
# Background task runner
# ---------------------------------------------------------------------------


def _run_summarisation(task_id: str, url: str, method: str, length: str) -> None:
    try:
        with _lock:
            _tasks[task_id].update(
                {"status": "processing", "progress": 10, "message": "Extracting article content…"}
            )

        result = _agent.run(url, method=method, length=length)  # type: ignore[union-attr]

        with _lock:
            if result.get("success"):
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

    except Exception as exc:
        logger.error("Task %s failed: %s", task_id, exc)
        with _lock:
            _tasks[task_id].update(
                {"status": "error", "progress": 0, "message": f"Internal error: {exc}"}
            )
            _results[task_id] = {"success": False, "error": str(exc)}
    finally:
        _evict_old_tasks()


# ---------------------------------------------------------------------------
# HTML routes
# ---------------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/historico")
def history():
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
    return render_template("history.html", tasks=completed)


@app.route("/sobre")
def about():
    return render_template("about.html")


@app.route("/configuracoes")
def settings():
    return render_template("settings.html")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@app.route("/api/sumarizar", methods=["POST"])
def api_summarise():
    """POST {url, method?, length?} → {success, task_id}"""
    # Rate limit
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
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
            {
                "success": False,
                "error": 'method must be "extractive" or "generative".',
            }
        ), 400

    length = data.get("length", "medium").lower()
    if length not in ("short", "medium", "long"):
        return jsonify(
            {
                "success": False,
                "error": 'length must be "short", "medium", or "long".',
            }
        ), 400

    task_id = str(uuid.uuid4())
    with _lock:
        _tasks[task_id] = {
            "status": "queued",
            "progress": 0,
            "message": "Queued…",
            "created_at": datetime.now().isoformat(),
            "url": url,
            "method": method,
            "length": length,
        }

    thread = threading.Thread(
        target=_run_summarisation,
        args=(task_id, url, method, length),
        daemon=True,
    )
    thread.start()

    logger.info("Task %s started: %s", task_id, url)
    return jsonify(
        {
            "success": True,
            "task_id": task_id,
            "message": "Summarisation started.",
        }
    )


@app.route("/api/tarefa/<task_id>", methods=["GET"])
def api_task_status(task_id: str):
    with _lock:
        if task_id not in _tasks:
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
            return jsonify({"success": False, "error": "Task not found."}), 404
        result = _results[task_id]

    if not result.get("success"):
        return jsonify({"success": False, "error": "Task did not succeed."}), 400

    files = result.get("files_created", {})
    if fmt not in files:
        return jsonify(
            {
                "success": False,
                "error": f"Format {fmt!r} not available. Options: {list(files)}",
            }
        ), 404

    path = files[fmt]
    # Security (M1): ensure the resolved path stays inside the configured output directory.
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
        return jsonify({"success": True, "status": _agent.get_status()})  # type: ignore[union-attr]
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/api/estatisticas", methods=["GET"])
def api_stats():
    with _lock:
        total = len(_tasks)
        done = sum(1 for t in _tasks.values() if t["status"] == "done")
        failed = sum(1 for t in _tasks.values() if t["status"] in ("failed", "error"))
        running = sum(1 for t in _tasks.values() if t["status"] in ("queued", "processing"))
    return jsonify(
        {
            "success": True,
            "stats": {
                "total": total,
                "done": done,
                "failed": failed,
                "running": running,
            },
        }
    )


@app.route("/api/limpar-cache", methods=["POST"])
def api_clear_cache():
    # Require a simple auth token to prevent unauthenticated cache clearing.
    # Security (C3): fail-closed — deny when ADMIN_TOKEN is unset OR token doesn't match.
    token = request.headers.get("X-Admin-Token", "")
    expected = os.getenv("ADMIN_TOKEN", "")
    if not expected or token != expected:
        return jsonify({"success": False, "error": "Unauthorised."}), 403

    if not _agent_ready:
        return jsonify({"success": False, "error": "Agent not initialised."}), 503
    try:
        _agent.file_manager.clear_cache()  # type: ignore[union-attr]
        return jsonify({"success": True, "message": "Cache cleared."})
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)}), 500


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "agent_ready": _agent_ready,
            "gemini_model": config.gemini.model_id,
            "summarization_method": config.summarization.method,
        }
    )


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
