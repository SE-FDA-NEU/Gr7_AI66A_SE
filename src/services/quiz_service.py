from pathlib import Path

from src.db import get_connection
from src.repositories.attempt_repository import get_open_attempt, get_submitted_attempt
from src.repositories.quiz_repository import (
    list_published_quizzes,
    list_published_quizzes_with_question_count,
)


def get_student_dashboard_data(db_path: str | Path):
    """
    Lấy danh sách quiz cho màn hình Dashboard sinh viên
    """
    conn = get_connection(db_path)
    try:
        quizzes = list_published_quizzes(conn)
        return quizzes
    finally:
        conn.close()


def get_student_quiz_statuses(db_path: str | Path, student_id: int):
    """
    Lấy danh sách quiz published kèm trạng thái của sinh viên:
    "submitted", "in_progress" hoặc "not_started"
    """
    conn = get_connection(db_path)
    try:
        quizzes = list_published_quizzes_with_question_count(conn)
        for quiz in quizzes:
            if get_submitted_attempt(conn, student_id, quiz["quiz_id"]) is not None:
                quiz["status"] = "submitted"
            elif get_open_attempt(conn, student_id, quiz["quiz_id"]) is not None:
                quiz["status"] = "in_progress"
            else:
                quiz["status"] = "not_started"
        return quizzes
    finally:
        conn.close()
