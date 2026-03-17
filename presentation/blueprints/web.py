"""Web blueprint — serves React SPA for all non-API routes."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, redirect, send_file, send_from_directory, url_for
from flask_jwt_extended import unset_jwt_cookies

web_bp = Blueprint("web", __name__)


def _serve_spa():
    index = Path(current_app.static_folder) / "dist" / "index.html"
    if index.exists():
        return send_file(str(index))
    # SPA not built — return a minimal placeholder so the API still works
    return (
        "<html><body><p>Frontend not built. Run <code>cd frontend && npm run build</code>.</p></body></html>",
        503,
    )


@web_bp.get("/")
def index():
    return _serve_spa()


@web_bp.get("/assets/<path:filename>")
def dist_assets(filename: str):
    """Serve Vite-built JS/CSS assets from static/dist/assets/.

    Must be declared before the catch-all so Flask matches it first and
    returns the correct MIME type instead of serving index.html.
    """
    dist_assets_dir = Path(current_app.static_folder) / "dist" / "assets"
    return send_from_directory(str(dist_assets_dir), filename)


@web_bp.get("/logout")
def logout():
    """Clear JWT cookies and redirect to root (React handles the login page)."""
    response = redirect(url_for("web.index"))
    unset_jwt_cookies(response)
    return response


@web_bp.get("/<path:path>")
def react_fallback(path: str):
    """Catch-all for React Router client-side routes.

    API and auth prefixes are intentionally excluded — their 404s are
    handled by the errorhandler in app_factory.py which returns JSON.
    """
    if path.startswith("api/") or path.startswith("auth/"):
        abort(404)
    return _serve_spa()
