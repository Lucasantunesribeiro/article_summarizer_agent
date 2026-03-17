"""Authentication blueprint."""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
)

from application.commands import AuthenticateUserCommand
from presentation.blueprints.helpers import enforce_rate_limit, get_container

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _build_tokens(user):
    additional_claims = {"role": user.role.value, "username": user.username}
    access_token = create_access_token(identity=user.id, additional_claims=additional_claims)
    refresh_token = create_refresh_token(identity=user.id, additional_claims=additional_claims)
    return access_token, refresh_token


@auth_bp.post("/login")
def api_login():
    limited = enforce_rate_limit("auth")
    if limited:
        return limited

    data = request.get_json(silent=True) or {}
    handler = get_container().authenticate_user_handler
    user = handler.handle(
        AuthenticateUserCommand(
            username=data.get("username", "").strip(),
            password=data.get("password", ""),
        )
    )
    if not user:
        return jsonify({"success": False, "error": "Invalid credentials."}), 401

    access_token, refresh_token = _build_tokens(user)
    response = jsonify(
        {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {"id": user.id, "username": user.username, "role": user.role.value},
        }
    )
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
    return response


@auth_bp.post("/register")
def api_register():
    limited = enforce_rate_limit("auth")
    if limited:
        return limited

    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required."}), 400

    container = get_container()
    if container.user_repository.get_by_username(username):
        return jsonify({"success": False, "error": "Username already taken."}), 409

    from datetime import datetime  # noqa: PLC0415
    from uuid import uuid4  # noqa: PLC0415

    from domain.entities import User, UserRole  # noqa: PLC0415

    user = User(
        id=str(uuid4()),
        username=username,
        password_hash=container.password_service.hash_password(password),
        role=UserRole.USER,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    container.user_repository.add(user)

    access_token, refresh_token = _build_tokens(user)
    resp = jsonify({"success": True, "username": user.username, "role": user.role.value})
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp, 201


@auth_bp.post("/logout")
def api_logout():
    response = jsonify({"success": True, "message": "Logged out."})
    unset_jwt_cookies(response)
    return response


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def api_refresh():
    container = get_container()
    user = container.user_repository.get_by_id(str(get_jwt_identity()))
    if not user or not user.is_active:
        return jsonify({"success": False, "error": "User not found."}), 404

    access_token = create_access_token(
        identity=user.id,
        additional_claims={"role": user.role.value, "username": user.username},
    )
    response = jsonify({"success": True, "access_token": access_token})
    set_access_cookies(response, access_token)
    return response


@auth_bp.get("/me")
@jwt_required()
def api_me():
    claims = get_jwt()
    return jsonify(
        {
            "success": True,
            "user": {
                "id": str(get_jwt_identity()),
                "username": claims.get("username"),
                "role": claims.get("role"),
            },
        }
    )
