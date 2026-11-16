"""Xác thực người dùng và kiểm tra quyền cho các route trên trình duyệt.

Module này kiểm tra mật khẩu, áp dụng khóa đăng nhập và cung cấp decorator
để route chỉ cho phép người đã đăng nhập với vai trò phù hợp truy cập.
"""
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
    DEFAULT_CLIENT_FAILURE_LIMIT,
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
    client_key: str = "",
    client_failure_limit: int = DEFAULT_CLIENT_FAILURE_LIMIT,
) -> AuthenticationResult:
    """Authenticate credentials and persist failed attempts in a rolling window.

    Failed attempts are counted per (email, client_key), so someone who guesses
    wrong passwords for an account only locks themselves out of it.
    """
    # Dùng thời gian Unix để so sánh thời điểm lỗi/khóa thống nhất trong SQLite.
    now = int(time.time())
    # Khóa ghi giúp kiểm tra và cập nhật số lần sai diễn ra như một giao dịch.
    connection.execute("BEGIN IMMEDIATE")

    try:
        # Nếu đã bị khóa theo tài khoản hoặc theo client thì không thử mật khẩu nữa.
        if get_active_lockout(connection, email, now, client_key) is not None:
            connection.commit()
            return AuthenticationResult(error_code=429)

        # Chỉ chấp nhận các vai trò hợp lệ; không tiết lộ email có tồn tại hay không.
        user = get_user_by_email(connection, email)
        if user is not None and user["role"] in {"lecturer", "student", "ta"}:
            password_is_valid = check_password_hash(user["password_hash"], password)
        else:
            password_is_valid = False

        # Đăng nhập đúng xóa lỗi của cặp tài khoản-client rồi trả về người dùng.
        if password_is_valid:
            clear_login_failures(connection, email, client_key)
            connection.commit()
            return AuthenticationResult(user=user)

        # Đăng nhập sai được ghi nhận; kết quả phân biệt sai mật khẩu và bị khóa.
        locked_until = record_login_failure(
            connection, email, now, client_key, client_failure_limit
        )
        connection.commit()
        return AuthenticationResult(error_code=429 if locked_until else 401)
    except Exception:
        connection.rollback()
        raise


def role_required(*roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Require an authenticated user whose role is one of the given roles."""

    def decorate(view: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            # Người chưa đăng nhập được chuyển đến login để tạo phiên làm việc.
            if session.get("user_id") is None:
                return redirect(url_for("auth.login"))

            # Đăng nhập không đủ: vai trò hiện tại cũng phải thuộc danh sách cho phép.
            if session.get("role") not in roles:
                return render_error(403)

            # Chỉ gọi route gốc sau khi cả xác thực và phân quyền đều thành công.
            return view(*args, **kwargs)

        return wrapped

    return decorate