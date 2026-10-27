from __future__ import annotations
"""Lecturer routes (US04, US12, Lecturer Dashboard)."""

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.auth import role_required
from src.db import get_connection
from src.errors import render_error
from src.repositories.audit_repository import get_attempt_audit_history
from src.services.lecturer_attempt_service import (
    LecturerAttemptError,
    get_quiz_attempt_detail,
    get_quiz_attempts,
)
from src.services.quiz_service import (
    InvalidQuiz,
    QuizServiceError,
    close_quiz,
    get_lecturer_dashboard_data,
    get_quiz_publish_details,
    publish_quiz,
    update_quiz_schedule,
)
from src.services.lecturer_attempt_service import (
    LecturerAttemptError,
    get_quiz_attempt_detail,
    get_quiz_attempts,
    get_quiz_statistics,
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


@lecturer_bp.get("/lecturer/quiz/<int:quiz_id>/attempts")
@role_required("lecturer")
def quiz_attempts(quiz_id: int):
    try:
        data = get_quiz_attempts(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
        )
    except LecturerAttemptError as error:
        return render_error(error.status_code, error.message)

    return render_template("lecturer_attempts.html", **data)


@lecturer_bp.get("/lecturer/quiz/<int:quiz_id>/attempts/<int:attempt_id>")
@role_required("lecturer")
def quiz_attempt_detail(quiz_id: int, attempt_id: int):
    try:
        data = get_quiz_attempt_detail(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
            attempt_id,
        )
    except LecturerAttemptError as error:
        return render_error(error.status_code, error.message)

    return render_template("lecturer_attempt_detail.html", **data)


@lecturer_bp.get("/lecturer/quiz/<int:quiz_id>/statistics")
@role_required("lecturer")
def quiz_statistics(quiz_id: int):
    try:
        data = get_quiz_statistics(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
        )
    except LecturerAttemptError as error:
        return render_error(error.status_code, error.message)

    return render_template("lecturer_statistics.html", **data)
@lecturer_bp.get("/lecturer/quiz/<int:quiz_id>/attempts/<int:attempt_id>/audit")
@role_required("lecturer")
def view_attempt_audit_history(quiz_id: int, attempt_id: int):
    """US12: Lecturer views an append-only attempt audit history."""
    db_path = current_app.config["DATABASE_PATH"]
    
    with get_connection(db_path) as connection:
        logs, error = get_attempt_audit_history(
            connection,
            attempt_id,
            session["user_id"],
        )

    if error == "ATTEMPT_NOT_FOUND":
        return render_error(404, "Attempt audit log not found.")
    if error == "NOT_QUIZ_OWNER":
        return render_error(
            403,
            "Bạn không có quyền xem nhật ký làm bài của quiz này vì nó thuộc giảng viên khác.",
        )

    return render_template(
        "lecturer_attempt_audit.html",
        logs=logs,
        attempt_id=attempt_id,
        quiz_id=quiz_id,
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
        start_at_local=data["start_at_local"],
        end_at_local=data["end_at_local"],
        schedule_error=None,
        messages=[],
        show_add_form=False,
    )


@lecturer_bp.post("/lecturer/quiz/<int:quiz_id>/schedule")
@role_required("lecturer")
def handle_quiz_schedule(quiz_id: int):
    db_path = current_app.config["DATABASE_PATH"]
    start_at_local = request.form.get("start_at", "")
    end_at_local = request.form.get("end_at", "")
    duration = request.form.get("duration")
    duration_unlimited = (
        request.form.get("duration_unlimited") == "yes"
        if "duration" in request.form or "duration_unlimited" in request.form
        else None
    )
    max_attempts = request.form.get("max_attempts")
    try:
        update_quiz_schedule(
            db_path,
            session["user_id"],
            quiz_id,
            start_at_local,
            end_at_local,
            duration,
            duration_unlimited,
            max_attempts,
        )
    except InvalidQuiz as error:
        try:
            data = get_quiz_publish_details(db_path, session["user_id"], quiz_id)
        except QuizServiceError as page_error:
            return render_error(page_error.status_code, page_error.message)
        return (
            render_template(
                "publish_quiz.html",
                quiz=data["quiz"],
                questions=data["questions"],
                is_publishable=data["is_publishable"],
                validation_error=data["validation_error"],
                start_at_local=start_at_local,
                end_at_local=end_at_local,
                schedule_error=str(error),
                duration=(
                    duration
                    if duration is not None
                    else data["quiz"]["duration_minutes"]
                ),
                duration_unlimited=(
                    bool(duration_unlimited)
                    if duration_unlimited is not None
                    else data["quiz"]["duration_unlimited"]
                ),
                max_attempts=(
                    max_attempts
                    if max_attempts is not None
                    else data["quiz"]["max_attempts"]
                ),
                messages=[],
                show_add_form=False,
            ),
            422,
        )
    except QuizServiceError as error:
        return render_error(error.status_code, error.message)

    flash("Quiz schedule saved successfully.", "success")
    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))


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
        if error.status_code == 403:
            return render_error(error.status_code, error.message)
        try:
            data = get_quiz_publish_details(
                current_app.config["DATABASE_PATH"],
                session["user_id"],
                quiz_id,
            )
            return (
                render_template(
                    "publish_quiz.html",
                    quiz=data["quiz"],
                    questions=data["questions"],
                    is_publishable=data["is_publishable"],
                    validation_error=error.message,
                    start_at_local=data["start_at_local"],
                    end_at_local=data["end_at_local"],
                    schedule_error=None,
                    messages=[],
                    show_add_form=False,
                ),
                error.status_code,
            )
        except Exception:
            return render_error(error.status_code, error.message)

    if request.is_json:
        return jsonify({"quiz_id": quiz["quiz_id"], "status": quiz["status"]}), 200

    flash("Quiz published successfully.", "success")
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
        if error.status_code == 403:
            return render_error(error.status_code, error.message)
        try:
            data = get_quiz_publish_details(
                current_app.config["DATABASE_PATH"],
                session["user_id"],
                quiz_id,
            )
            return (
                render_template(
                    "publish_quiz.html",
                    quiz=data["quiz"],
                    questions=data["questions"],
                    is_publishable=data["is_publishable"],
                    validation_error=error.message,
                    start_at_local=data["start_at_local"],
                    end_at_local=data["end_at_local"],
                    schedule_error=None,
                    messages=[],
                    show_add_form=False,
                ),
                error.status_code,
            )
        except Exception:
            return render_error(error.status_code, error.message)

    if request.is_json:
        return jsonify({"quiz_id": quiz["quiz_id"], "status": quiz["status"]}), 200

    flash("Quiz closed successfully.", "success")
    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))