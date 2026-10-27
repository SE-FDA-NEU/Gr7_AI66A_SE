"""Authentication and role checks for browser routes."""
from __future__ import annotations
import sqlite3
import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

from flask import redirect, session, url_for
from werkzeug.security import check_password_hash

from src.errors import render_error
from src.repositories.auth_repository import (
    clear_login_failures,
    get_active_lockout,
    get_user_by_email,
    record_login_failure,
)


@dataclass(frozen=True)
class AuthenticationResult:
    """The result of checking credentials and applying the login lockout rule."""

    user: sqlite3.Row | None = None
    error_code: int | None = None


def authenticate_user(
    connection: sqlite3.Connection,
    email: str,
    password: str,
) -> AuthenticationResult:
    """Authenticate credentials and persist failed attempts in a rolling window."""
    now = int(time.time())
    connection.execute("BEGIN IMMEDIATE")

    try:
        if get_active_lockout(connection, email, now) is not None:
            connection.commit()
            return AuthenticationResult(error_code=429)

        user = get_user_by_email(connection, email)
        if user is not None and user["role"] in {"lecturer", "student"}:
            password_is_valid = check_password_hash(user["password_hash"], password)
        else:
            password_is_valid = False

        if password_is_valid:
            clear_login_failures(connection, email)
            connection.commit()
            return AuthenticationResult(user=user)

        locked_until = record_login_failure(connection, email, now)
        connection.commit()
        return AuthenticationResult(error_code=429 if locked_until else 401)
    except Exception:
        connection.rollback()
        raise


def role_required(role: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Require an authenticated user with the requested role."""

    def decorate(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            if session.get("user_id") is None:
                return redirect(url_for("auth.login"))

            if session.get("role") != role:
                return render_error(403)

            return view(*args, **kwargs)

        return wrapped

    return decorate