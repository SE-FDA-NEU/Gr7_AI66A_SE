from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from src.auth import role_required
from src.errors import render_error
from src.services.attempt_service import (
    AttemptError,
    get_take_page_data,
    save_answer,
    start_attempt,
)
from src.services.quiz_service import get_student_dashboard_data

student_bp = Blueprint("student", __name__)


@student_bp.route("/student/dashboard", methods=["GET"])
@role_required("student")
def student_dashboard():
    quizzes = get_student_dashboard_data(current_app.config["DATABASE_PATH"])
    return render_template("student_dashboard.html", quizzes=quizzes)


@student_bp.post("/student/quiz/<int:quiz_id>/start")
@role_required("student")
def start_quiz(quiz_id):
    try:
        start_attempt(current_app.config["DATABASE_PATH"], session["user_id"], quiz_id)
    except AttemptError as error:
        return render_error(error.status_code, error.message)
    return redirect(url_for("student.take_quiz", quiz_id=quiz_id, q=1))


@student_bp.get("/student/quiz/<int:quiz_id>/take")
@role_required("student")
def take_quiz(quiz_id):
    question_number = request.args.get("q", default=1, type=int)
    try:
        data = get_take_page_data(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
            question_number,
        )
    except AttemptError as error:
        return render_error(error.status_code, error.message)
    return render_template("take_quiz.html", **data)


@student_bp.post("/student/quiz/<int:quiz_id>/take")
@role_required("student")
def save_quiz_answer(quiz_id):
    attempt_id = request.form.get("attempt_id", type=int)
    question_id = request.form.get("question_id", type=int)
    choice_id = request.form.get("choice_id", type=int)
    go_to = request.form.get("go", default=1, type=int)
    if attempt_id is None or question_id is None:
        return render_error(400, "The answer form was incomplete. Reload the question and try again.")

    if choice_id is not None:
        try:
            save_answer(
                current_app.config["DATABASE_PATH"],
                session["user_id"],
                quiz_id,
                attempt_id,
                question_id,
                choice_id,
            )
        except AttemptError as error:
            return render_error(error.status_code, error.message)

    # Post/Redirect/Get: refreshing the next page does not resend the form.
    return redirect(url_for("student.take_quiz", quiz_id=quiz_id, q=go_to))
