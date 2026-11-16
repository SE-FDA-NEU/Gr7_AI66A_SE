"""Các endpoint JSON mà giao diện tải bất đồng bộ bằng JavaScript."""
from __future__ import annotations

from flask import Blueprint, current_app, session, url_for

from src.auth import role_required
from src.services.quiz_service import get_student_quiz_statuses

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/student/quizzes")
@role_required("student")
def student_quizzes():
    # Chỉ sinh viên đăng nhập được gọi API này; service tạo trạng thái từng quiz.
    quizzes = get_student_quiz_statuses(current_app.config["DATABASE_PATH"], session["user_id"])
    # Gửi kèm URL đã được Flask tạo để JS không phải tự ghép đường dẫn.
    for quiz in quizzes:
        quiz["start_url"] = url_for("student.start_quiz", quiz_id=quiz["quiz_id"])
    return {"quizzes": quizzes}
