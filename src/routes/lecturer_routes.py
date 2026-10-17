"""Lecturer dashboard route."""

from flask import Blueprint, render_template, session

from src.auth import role_required

lecturer_bp = Blueprint("lecturer", __name__)


@lecturer_bp.get("/lecturer/dashboard")
@role_required("lecturer")
def lecturer_dashboard():
    return render_template("lecturer_dashboard.html", name=session.get("name", "Lecturer"))
