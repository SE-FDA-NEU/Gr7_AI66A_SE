from __future__ import annotations
"""Read-only lecturer views of student quiz attempts."""

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


def _owned_quiz(connection, lecturer_id: int, quiz_id: int):
    quiz = get_quiz_by_id(connection, quiz_id)
    if quiz is None:
        raise LecturerAttemptError(404, errors.QUIZ_NOT_FOUND)
    if quiz["lecturer_id"] != lecturer_id:
        raise LecturerAttemptError(403, errors.NOT_QUIZ_OWNER)
    return quiz


def get_quiz_attempts(
    db_path: str | Path,
    lecturer_id: int,
    quiz_id: int,
) -> dict:
    with closing(get_connection(db_path)) as connection:
        quiz = _owned_quiz(connection, lecturer_id, quiz_id)
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
) -> dict:
    with closing(get_connection(db_path)) as connection:
        quiz = _owned_quiz(connection, lecturer_id, quiz_id)
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
