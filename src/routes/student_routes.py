from flask import Blueprint, current_app, render_template
from src.services.quiz_service import get_student_dashboard_data

student_bp = Blueprint("student", __name__)


@student_bp.route("/student/dashboard", methods=["GET"])
def student_dashboard():
    quizzes = get_student_dashboard_data(current_app.config["DATABASE_PATH"])
    return render_template("student_dashboard.html", quizzes=quizzes)