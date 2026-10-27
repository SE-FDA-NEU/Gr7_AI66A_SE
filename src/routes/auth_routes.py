from __future__ import annotations
"""Login and logout routes."""

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
from src.db import get_connection
from src.errors import error_message

auth_bp = Blueprint("auth", __name__)


def _dashboard_for_role(role: str) -> str:
    if role == "lecturer":
        return url_for("lecturer.lecturer_dashboard")
    return url_for("student.student_dashboard")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") is not None:
        return redirect(_dashboard_for_role(session["role"]))

    if request.method == "GET":
        return render_template("login.html")

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

    connection = get_connection(current_app.config["DATABASE_PATH"])
    try:
        result = authenticate_user(connection, email, password)
    finally:
        connection.close()

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

    session.clear()
    session["user_id"] = result.user["user_id"]
    session["name"] = result.user["name"]
    session["role"] = result.user["role"]
    return redirect(_dashboard_for_role(result.user["role"]))


@auth_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
