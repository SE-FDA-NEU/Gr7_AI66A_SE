"""Lecturer routes (US04, Lecturer Dashboard)."""

from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.auth import role_required
from src.errors import render_error
from src.services.quiz_service import (
    QuizServiceError,
    close_quiz,
    get_lecturer_dashboard_data,
    get_quiz_publish_details,
    publish_quiz,
)

lecturer_bp = Blueprint("lecturer", __name__)


@lecturer_bp.get("/lecturer/dashboard")
@role_required("lecturer")
def lecturer_dashboard():
    quizzes = get_lecturer_dashboard_data(
        current_app.config["DATABASE_PATH"],
        session["user_id"],
    )
    return render_template(
        "lecturer_dashboard.html",
        name=session.get("name", "Lecturer"),
        quizzes=quizzes,
    )


@lecturer_bp.get("/lecturer/quiz/<int:quiz_id>/publish")
@role_required("lecturer")
def publish_page(quiz_id: int):
    try:
        data = get_quiz_publish_details(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
        )
    except QuizServiceError as error:
        return render_error(error.status_code, error.message)

    return render_template(
        "publish_quiz.html",
        quiz=data["quiz"],
        questions=data["questions"],
        is_publishable=data["is_publishable"],
        validation_error=data["validation_error"],
    )


@lecturer_bp.post("/lecturer/quiz/<int:quiz_id>/publish")
@role_required("lecturer")
def handle_publish_quiz(quiz_id: int):
    try:
        quiz = publish_quiz(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
        )
    except QuizServiceError as error:
        if request.is_json:
            return jsonify({"error": error.message}), error.status_code
        return render_error(error.status_code, error.message)

    if request.is_json:
        return jsonify({"quiz_id": quiz["quiz_id"], "status": quiz["status"]}), 200

    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))


@lecturer_bp.post("/lecturer/quiz/<int:quiz_id>/close")
@role_required("lecturer")
def handle_close_quiz(quiz_id: int):
    try:
        quiz = close_quiz(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
        )
    except QuizServiceError as error:
        if request.is_json:
            return jsonify({"error": error.message}), error.status_code
        return render_error(error.status_code, error.message)

    if request.is_json:
        return jsonify({"quiz_id": quiz["quiz_id"], "status": quiz["status"]}), 200

    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))
