"""Chuẩn bị dữ liệu chỉ đọc về lượt làm bài cho khu vực giảng viên."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path

from src import errors
from src.db import get_connection
from src.repositories import attempt_repository
from src.repositories.quiz_repository import get_quiz_by_id
from src.services.attempt_service import format_vietnam_time


class LecturerAttemptError(Exception):
    """A lecturer attempt page could not be loaded."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _owned_quiz(connection, lecturer_id: int, quiz_id: int, role: str = "lecturer"):
    # Trợ giảng có thể xem theo vai trò; giảng viên thường chỉ xem quiz của mình.
    quiz = get_quiz_by_id(connection, quiz_id)
    if quiz is None:
        raise LecturerAttemptError(404, errors.QUIZ_NOT_FOUND)
    if role != "ta" and quiz["lecturer_id"] != lecturer_id:
        raise LecturerAttemptError(403, errors.NOT_QUIZ_OWNER)
    return quiz


def get_quiz_attempts(
    db_path: str | Path,
    lecturer_id: int,
    quiz_id: int,
    role: str = "lecturer"
) -> dict:
    with closing(get_connection(db_path)) as connection:
        # Xác thực quyền trước khi truy vấn danh sách kết quả sinh viên.
        quiz = _owned_quiz(connection, lecturer_id, quiz_id, role)
        attempts = attempt_repository.list_quiz_attempts(connection, quiz_id)
        for attempt in attempts:
            attempt["started_at_display"] = format_vietnam_time(attempt["started_at"])
            attempt["submitted_at_display"] = (
                format_vietnam_time(attempt["submitted_at"])
                if attempt["submitted_at"]
                else None
            )
        return {"quiz": quiz, "attempts": attempts}


def get_quiz_attempt_detail(
    db_path: str | Path,
    lecturer_id: int,
    quiz_id: int,
    attempt_id: int,
    role: str = "lecturer"
) -> dict:
    with closing(get_connection(db_path)) as connection:
        quiz = _owned_quiz(connection, lecturer_id, quiz_id, role)
        # Ràng buộc cả attempt_id lẫn quiz_id để ID từ URL không lộ attempt quiz khác.
        attempt = connection.execute(
            """
            SELECT
                a.attempt_id,
                a.student_id,
                u.name AS student_name,
                u.email AS student_email,
                a.started_at,
                a.submitted_at,
                a.score
            FROM attempt a
            JOIN user u ON u.user_id = a.student_id
            WHERE a.attempt_id = ? AND a.quiz_id = ?
            """,
            (attempt_id, quiz_id),
        ).fetchone()
        if attempt is None:
            raise LecturerAttemptError(404, errors.ATTEMPT_NOT_FOUND)

        attempt_data = dict(attempt)
        attempt_data["started_at_display"] = format_vietnam_time(attempt["started_at"])
        attempt_data["submitted_at_display"] = (
            format_vietnam_time(attempt["submitted_at"])
            if attempt["submitted_at"]
            else None
        )
        answers = attempt_repository.get_attempt_answers(connection, attempt_id)
        return {"quiz": quiz, "attempt": attempt_data, "answers": answers}


def get_quiz_statistics(
    db_path: str | Path,
    lecturer_id: int,
    quiz_id: int,
    role: str = "lecturer"
) -> dict:
    """Return submitted-attempt and per-question statistics for an owned quiz."""
    with closing(get_connection(db_path)) as connection:
        quiz = _owned_quiz(connection, lecturer_id, quiz_id, role)
        # Chỉ attempt đã submit được tính vào điểm trung bình và tỷ lệ đúng.
        summary = connection.execute(
            """
            SELECT COUNT(*) AS submitted_attempts,
                   COALESCE(AVG(score), 0) AS average_score
            FROM attempt
            WHERE quiz_id = ? AND submitted_at IS NOT NULL
            """,
            (quiz_id,),
        ).fetchone()

        questions = connection.execute(
            """
            SELECT q.question_id, q.position, q.content,
                   COUNT(DISTINCT a.attempt_id) AS submitted_attempts,
                   COALESCE(SUM(CASE WHEN c.is_correct = 1 THEN 1 ELSE 0 END), 0)
                       AS correct_answers
            FROM question q
            LEFT JOIN attempt a
                ON a.quiz_id = q.quiz_id AND a.submitted_at IS NOT NULL
            LEFT JOIN answer ans
                ON ans.attempt_id = a.attempt_id AND ans.question_id = q.question_id
            LEFT JOIN choice c ON c.choice_id = ans.choice_id
            WHERE q.quiz_id = ?
            GROUP BY q.question_id
            ORDER BY q.position
            """,
            (quiz_id,),
        ).fetchall()

        # Tính phần trăm đúng theo số lượt đã nộp; không chia khi mẫu số bằng 0.
        question_statistics = []
        for question in questions:
            question_data = dict(question)
            denominator = question_data["submitted_attempts"]
            question_data["correct_rate"] = (
                question_data["correct_answers"] / denominator if denominator else 0
            )
            question_statistics.append(question_data)

        return {
            "quiz": quiz,
            "submitted_attempts": summary["submitted_attempts"],
            "average_score": summary["average_score"],
            "questions": question_statistics,
        }
