"""HTML blueprint."""

from __future__ import annotations

from flask import Blueprint, g, redirect, render_template, request, url_for
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
)

from application.commands import AuthenticateUserCommand
from application.queries import GetSettingsQuery, ListTaskHistoryQuery
from presentation.blueprints.helpers import get_container

web_bp = Blueprint("web", __name__)


@web_bp.get("/")
def index():
    settings_data = get_container().get_settings_handler.handle(GetSettingsQuery())
    return render_template(
        "index.html",
        settings_data=settings_data,
        csp_nonce=g.csp_nonce,
    )


@web_bp.get("/historico")
def history():
    try:
        verify_jwt_in_request(locations=["cookies"])
    except Exception:
        return redirect(url_for("web.login", next=request.url))

    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    data = get_container().list_task_history_handler.handle(
        ListTaskHistoryQuery(page=max(page, 1), per_page=per_page)
    )
    return render_template("history.html", csp_nonce=g.csp_nonce, **data)


@web_bp.get("/sobre")
def about():
    return render_template("about.html", csp_nonce=g.csp_nonce)


@web_bp.get("/configuracoes")
def settings():
    try:
        verify_jwt_in_request(locations=["cookies"])
    except Exception:
        return redirect(url_for("web.login", next=request.url))

    settings_data = get_container().get_settings_handler.handle(GetSettingsQuery())
    return render_template("settings.html", settings_data=settings_data, csp_nonce=g.csp_nonce)


@web_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = get_container().authenticate_user_handler.handle(
            AuthenticateUserCommand(
                username=request.form.get("username", "").strip(),
                password=request.form.get("password", ""),
            )
        )
        if not user:
            return render_template(
                "login.html",
                error="Invalid credentials.",
                csp_nonce=g.csp_nonce,
            )

        access_token = create_access_token(
            identity=user.id,
            additional_claims={"role": user.role.value, "username": user.username},
        )
        refresh_token = create_refresh_token(
            identity=user.id,
            additional_claims={"role": user.role.value, "username": user.username},
        )
        response = redirect(request.args.get("next", url_for("web.history")))
        set_access_cookies(response, access_token)
        set_refresh_cookies(response, refresh_token)
        return response

    return render_template("login.html", error=None, csp_nonce=g.csp_nonce)


@web_bp.get("/logout")
def logout():
    response = redirect(url_for("web.index"))
    unset_jwt_cookies(response)
    return response


@web_bp.get("/<path:path>")
def react_fallback(path: str):
    from pathlib import Path

    from flask import abort, current_app, send_file

    index = Path(current_app.static_folder) / "dist" / "index.html"
    if index.exists():
        return send_file(str(index))
    abort(404)
