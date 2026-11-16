"""Các route để sinh viên bắt đầu, làm, xem lại và nộp bài quiz."""
from __future__ import annotations
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for
from src.auth import role_required
from src.errors import AUTO_SUBMITTED, UNANSWERED_NOT_CONFIRMED, render_error
from src.services.attempt_service import (
    AttemptError,
    AutoSubmitted,
    UnansweredNotConfirmed,
    get_review_data,
    get_submitted_data,
    get_take_page_data,
    save_answer,
    start_attempt,
    submit_attempt,
)
from src.services.quiz_service import get_student_dashboard_data

student_bp = Blueprint("student", __name__)


def _auto_submitted_redirect(quiz_id):
    # Đưa người học đến trang kết quả và báo rõ bài đã tự nộp vì hết giờ.
    return redirect(url_for("student.quiz_submitted", quiz_id=quiz_id, timeout=1))


@student_bp.route("/student/dashboard", methods=["GET"])
@role_required("student")
def student_dashboard():
    # Service cung cấp danh sách quiz cùng trạng thái làm bài của sinh viên.
    quizzes = get_student_dashboard_data(current_app.config["DATABASE_PATH"])
    return render_template("student_dashboard.html", quizzes=quizzes)


@student_bp.post("/student/quiz/<int:quiz_id>/start")
@role_required("student")
def start_quiz(quiz_id):
    # Service tạo lượt làm mới hoặc tiếp tục lượt đang mở trước khi chuyển trang.
    try:
        start_attempt(current_app.config["DATABASE_PATH"], session["user_id"], quiz_id)
    except AttemptError as error:
        return render_error(error.status_code, error.message)
    return redirect(url_for("student.take_quiz", quiz_id=quiz_id, q=1))


@student_bp.get("/student/quiz/<int:quiz_id>/take")
@role_required("student")
def take_quiz(quiz_id):
    # Số câu được truyền qua query string; mặc định hiển thị câu đầu tiên.
    question_number = request.args.get("q", default=1, type=int)
    try:
        data = get_take_page_data(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
            question_number,
        )
    except AutoSubmitted:
        return _auto_submitted_redirect(quiz_id)
    except AttemptError as error:
        return render_error(error.status_code, error.message)
    return render_template("take_quiz.html", **data)


@student_bp.post("/student/quiz/<int:quiz_id>/take")
@role_required("student")
def save_quiz_answer(quiz_id):
    # Lấy các ID từ form để service xác minh quyền sở hữu và tính hợp lệ.
    attempt_id = request.form.get("attempt_id", type=int)
    question_id = request.form.get("question_id", type=int)
    choice_id = request.form.get("choice_id", type=int)
    go_to = request.form.get("go", default="1")
    if attempt_id is None or question_id is None:
        return render_error(400, "The answer form was incomplete. Reload the question and try again.")

    # Không chọn đáp án vẫn có thể chuyển câu; chỉ lưu khi người dùng đã chọn.
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
        except AutoSubmitted:
            return _auto_submitted_redirect(quiz_id)
        except AttemptError as error:
            return render_error(error.status_code, error.message)

    # Post/Redirect/Get: refreshing trang kế tiếp không gửi lại form POST.
    if go_to == "review":
        return redirect(url_for("student.review_quiz", quiz_id=quiz_id))
    question_number = int(go_to) if go_to.isdigit() else 1
    return redirect(url_for("student.take_quiz", quiz_id=quiz_id, q=question_number))


@student_bp.get("/student/quiz/<int:quiz_id>/review")
@role_required("student")
def review_quiz(quiz_id):
    # Trang review tóm tắt câu đã trả lời và câu còn bỏ trống.
    try:
        data = get_review_data(current_app.config["DATABASE_PATH"], session["user_id"], quiz_id)
    except AutoSubmitted:
        return _auto_submitted_redirect(quiz_id)
    except AttemptError as error:
        return render_error(error.status_code, error.message)
    return render_template("review_quiz.html", **data)


@student_bp.post("/student/quiz/<int:quiz_id>/submit")
@role_required("student")
def submit_quiz(quiz_id):
    # Xác nhận nộp bài được truyền rõ ràng để service xử lý câu chưa trả lời.
    attempt_id = request.form.get("attempt_id", type=int)
    if attempt_id is None:
        return render_error(400, "The submit form was incomplete. Reload the review page and try again.")

    try:
        submit_attempt(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
            attempt_id,
            confirmed=request.form.get("confirm") == "yes",
        )
    except AutoSubmitted:
        return _auto_submitted_redirect(quiz_id)
    except UnansweredNotConfirmed as pending:
        return (
            render_template("review_quiz.html", error=UNANSWERED_NOT_CONFIRMED, **pending.review),
            422,
        )
    except AttemptError as error:
        return render_error(error.status_code, error.message)
    return redirect(url_for("student.quiz_submitted", quiz_id=quiz_id))


@student_bp.get("/student/quiz/<int:quiz_id>/submitted")
@role_required("student")
def quiz_submitted(quiz_id):
    # Trang này chỉ hiển thị kết quả nếu service tìm được lượt đã nộp của user.
    try:
        data = get_submitted_data(current_app.config["DATABASE_PATH"], session["user_id"], quiz_id)
    except AttemptError as error:
        return render_error(error.status_code, error.message)
    return render_template(
        "quiz_submitted.html",
        notice=AUTO_SUBMITTED if request.args.get("timeout") == "1" else None,
        submitted_successfully=request.args.get("timeout") != "1",
        **data,
    )
