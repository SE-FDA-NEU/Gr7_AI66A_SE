
from pathlib import Path

from src.db import get_connection

from src.repositories.attempt_repository import (
    get_open_attempt,
    get_submitted_attempt,
)

from src.repositories.quiz_repository import (
    create_quiz,
    list_published_quizzes,
    list_published_quizzes_with_question_count,
)


# ==========================================
# STUDENT DASHBOARD
# ==========================================

def get_student_dashboard_data(db_path: str | Path):
    """
    Lấy danh sách quiz đã publish
    cho màn hình Dashboard sinh viên.
    """
    conn = get_connection(db_path)

    try:
        quizzes = list_published_quizzes(conn)
        return quizzes
    finally:
        conn.close()


def get_student_quiz_statuses(db_path: str | Path, student_id: int):
    """
    Lấy danh sách quiz đã publish kèm trạng thái sinh viên:
    - submitted
    - in_progress
    - not_started
    """
    conn = get_connection(db_path)

    try:
        quizzes = list_published_quizzes_with_question_count(conn)

        for quiz in quizzes:
            quiz_id = quiz["quiz_id"]

            if get_submitted_attempt(
                conn, student_id, quiz_id
            ) is not None:
                quiz["status"] = "submitted"

            elif get_open_attempt(
                conn, student_id, quiz_id
            ) is not None:
                quiz["status"] = "in_progress"

            else:
                quiz["status"] = "not_started"

        return quizzes

    finally:
        conn.close()


# ==========================================
# US02 - CREATE QUIZ
# ==========================================

class InvalidQuiz(Exception):
    """Raised when quiz creation data is invalid."""


def create_new_quiz(
    db_path: str | Path,
    lecturer_id: int,
    title: str,
    duration: str,
    description: str = "",
) -> int:
    """
    Validate input and create a draft quiz.

    - Title is required.
    - Duration must be a positive integer.
    - Description is optional.
    - New quiz status is draft.
    """

    title = title.strip()
    description = description.strip()

    if not title:
        raise InvalidQuiz("Quiz title is required.")

    try:
        duration_minutes = int(duration)
    except (ValueError, TypeError):
        raise InvalidQuiz(
            "Duration must be a positive number."
        )

    if duration_minutes <= 0:
        raise InvalidQuiz(
            "Duration must be a positive number."
        )

    conn = get_connection(db_path)

    try:
        quiz_id = create_quiz(
            conn,
            lecturer_id,
            title,
            duration_minutes,
            description,
        )

        return quiz_id

    finally:
        conn.close()
