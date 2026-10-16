from flask import Blueprint, current_app, render_template
from src.auth import role_required
from src.services.quiz_service import get_student_dashboard_data

student_bp = Blueprint("student", __name__)


@student_bp.route("/student/dashboard", methods=["GET"])
@role_required("student")
def student_dashboard():
    quizzes = get_student_dashboard_data(current_app.config["DATABASE_PATH"])
    return render_template("student_dashboard.html", quizzes=quizzes)