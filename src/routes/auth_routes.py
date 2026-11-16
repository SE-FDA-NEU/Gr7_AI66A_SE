"""Các URL đăng nhập/đăng xuất; kết nối form HTTP với dịch vụ xác thực."""
from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.auth import authenticate_user
from src.client_identity import client_key
from src.db import get_connection
from src.errors import error_message
from src.repositories.auth_repository import DEFAULT_CLIENT_FAILURE_LIMIT

auth_bp = Blueprint("auth", __name__)


def _dashboard_for_role(role: str) -> str:
    # Trợ giảng dùng chung khu vực thao tác với giảng viên.
    if role in {"lecturer", "ta"}:
        return url_for("lecturer.lecturer_dashboard")
    return url_for("student.student_dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    # Người đã có phiên không cần nhập lại thông tin đăng nhập.
    if session.get("user_id") is not None:
        return redirect(_dashboard_for_role(session["role"]))

    if request.method == "GET":
        return render_template("login.html")

    # Chuẩn hóa email, nhưng không sửa mật khẩu vì khoảng trắng có thể có ý nghĩa.
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    if not email or not password:
        return (
            render_template(
                "login.html",
                error=error_message(400),
                status_code=400,
                email=email,
            ),
            400,
        )

    # Mở kết nối chỉ trong lúc xác thực và luôn đóng kể cả khi có lỗi.
    connection = get_connection(current_app.config["DATABASE_PATH"])
    try:
        result = authenticate_user(
            connection,
            email,
            password,
            client_key=client_key(
                request.remote_addr, current_app.config["SECRET_KEY"]
            ),
            client_failure_limit=current_app.config.get(
                "LOGIN_CLIENT_FAILURE_LIMIT", DEFAULT_CLIENT_FAILURE_LIMIT
            ),
        )
    finally:
        connection.close()

    # Thông tin lỗi được hiển thị chung, không tiết lộ tài khoản có tồn tại.
    if result.user is None:
        status_code = result.error_code or 401
        return (
            render_template(
                "login.html",
                error=error_message(status_code),
                status_code=status_code,
                email=email,
            ),
            status_code,
        )

    # Xóa dữ liệu phiên cũ trước khi ghi danh tính của phiên đăng nhập mới.
    session.clear()
    session["user_id"] = result.user["user_id"]
    session["name"] = result.user["name"]
    session["role"] = result.user["role"]
    return redirect(_dashboard_for_role(result.user["role"]))


@auth_bp.post("/logout")
def logout():
    # Xóa toàn bộ thông tin phiên để đăng xuất ở phía server/browser.
    session.clear()
    return redirect(url_for("auth.login"))
