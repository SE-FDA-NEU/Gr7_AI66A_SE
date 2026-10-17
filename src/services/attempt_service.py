"""Business rules for starting a quiz attempt and saving answers (US06, BR4, BR5)."""

from datetime import datetime, timezone
from pathlib import Path

from src import errors
from src.db import get_connection
from src.repositories import attempt_repository as repo

TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S"


class AttemptError(Exception):
    """A rule violation that the route shows to the student as an error page."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def _now() -> datetime:
    """Current UTC time; tests monkeypatch this to control the clock."""
    return datetime.now(timezone.utc).replace(microsecond=0, tzinfo=None)


def remaining_seconds(
    started_at: str,
    duration_minutes: int,
    now: datetime | None = None,
) -> int:
    """Seconds left in the attempt: quiz duration minus time elapsed since start."""
    now = now or _now()
    elapsed = (now - datetime.strptime(started_at, TIMESTAMP_FORMAT)).total_seconds()
    return max(0, int(duration_minutes * 60 - elapsed))


def _check_quiz_can_start(quiz) -> None:
    """BR4: only published quizzes can be started."""
    if quiz is None:
        raise AttemptError(404, errors.QUIZ_NOT_FOUND)
    if quiz["status"] == "closed":
        raise AttemptError(403, errors.QUIZ_CLOSED)
    if quiz["status"] != "published":
        raise AttemptError(403, errors.QUIZ_NOT_PUBLISHED)


def start_attempt(db_path: str | Path, student_id: int, quiz_id: int) -> dict:
    """Resume the student's open attempt or create a new one."""
    connection = get_connection(db_path)
    try:
        # Lock before checking so two simultaneous starts cannot both create an attempt.
        connection.execute("BEGIN IMMEDIATE")
        _check_quiz_can_start(repo.get_quiz(connection, quiz_id))

        # BR5: one submission per student and quiz.
        if repo.get_submitted_attempt(connection, student_id, quiz_id) is not None:
            raise AttemptError(409, errors.ALREADY_SUBMITTED)

        attempt = repo.get_open_attempt(connection, student_id, quiz_id)
        if attempt is None:
            attempt_id = repo.create_attempt(
                connection,
                student_id,
                quiz_id,
                _now().strftime(TIMESTAMP_FORMAT),
            )
            attempt = repo.get_attempt(connection, attempt_id)

        connection.commit()
        return dict(attempt)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_take_page_data(
    db_path: str | Path,
    student_id: int,
    quiz_id: int,
    question_number: int,
) -> dict:
    """Everything the take-quiz page needs to show one question."""
    connection = get_connection(db_path)
    try:
        quiz = repo.get_quiz(connection, quiz_id)
        if quiz is None:
            raise AttemptError(404, errors.QUIZ_NOT_FOUND)

        attempt = repo.get_open_attempt(connection, student_id, quiz_id)
        if attempt is None:
            if repo.get_submitted_attempt(connection, student_id, quiz_id) is not None:
                raise AttemptError(409, errors.ALREADY_SUBMITTED)
            raise AttemptError(404, errors.ATTEMPT_NOT_STARTED)

        questions = repo.list_questions_with_choices(connection, quiz_id)
        if not 1 <= question_number <= len(questions):
            raise AttemptError(404, errors.QUESTION_NOT_FOUND)

        selected = repo.get_selected_choices(connection, attempt["attempt_id"])
        question = questions[question_number - 1]
        return {
            "quiz": dict(quiz),
            "attempt_id": attempt["attempt_id"],
            "question": question,
            "question_number": question_number,
            "total_questions": len(questions),
            "selected_choice_id": selected.get(question["question_id"]),
            "answered_numbers": [
                number
                for number, item in enumerate(questions, start=1)
                if selected.get(item["question_id"]) is not None
            ],
            "remaining_seconds": remaining_seconds(
                attempt["started_at"], quiz["duration_minutes"]
            ),
        }
    finally:
        connection.close()


def save_answer(
    db_path: str | Path,
    student_id: int,
    quiz_id: int,
    attempt_id: int,
    question_id: int,
    choice_id: int,
) -> None:
    """Save or replace the student's choice for one question of an open attempt."""
    connection = get_connection(db_path)
    try:
        attempt = repo.get_attempt(connection, attempt_id)
        if (
            attempt is None
            or attempt["student_id"] != student_id
            or attempt["quiz_id"] != quiz_id
        ):
            raise AttemptError(403, errors.NOT_YOUR_ATTEMPT)
        if attempt["submitted_at"] is not None:
            raise AttemptError(409, errors.ALREADY_SUBMITTED)

        quiz = repo.get_quiz(connection, quiz_id)
        if remaining_seconds(attempt["started_at"], quiz["duration_minutes"]) == 0:
            raise AttemptError(403, errors.TIME_IS_UP)
        if not repo.choice_belongs_to_question(connection, choice_id, question_id, quiz_id):
            raise AttemptError(400, errors.INVALID_CHOICE)

        repo.upsert_answer(connection, attempt_id, question_id, choice_id)
        connection.commit()
    finally:
        connection.close()
