"""Business rules for taking and submitting a quiz attempt (US06, US08, BR4, BR5, BR6)."""

from datetime import datetime, timedelta
from pathlib import Path

from src import errors
from src.db import get_connection
from src.repositories import attempt_repository as repo
from src.repositories.quiz_repository import close_expired_published_quizzes
from src.time_utils import (
    TIMESTAMP_FORMAT,
    format_vietnam_time as format_vietnam_timestamp,
    parse_utc_timestamp,
    utc_now_naive,
)


class AttemptError(Exception):
    """A rule violation that the route shows to the student as an error page."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class AutoSubmitted(Exception):
    """The attempt ran out of time and has just been submitted automatically."""

    def __init__(self, quiz_id: int):
        super().__init__(quiz_id)
        self.quiz_id = quiz_id


class UnansweredNotConfirmed(Exception):
    """Submission needs explicit confirmation because questions are unanswered."""

    def __init__(self, review: dict):
        super().__init__(errors.UNANSWERED_NOT_CONFIRMED)
        self.review = review


def _now() -> datetime:
    """Current UTC time; tests monkeypatch this to control the clock."""
    return utc_now_naive()


def remaining_seconds(
    started_at: str,
    duration_minutes: int | None,
    now: datetime | None = None,
    end_at: str | None = None,
) -> int | None:
    """Return seconds until the earliest configured limit, or None if unlimited."""
    now = now or _now()
    deadlines = []
    if duration_minutes is not None:
        deadlines.append(
            datetime.strptime(started_at, TIMESTAMP_FORMAT)
            + timedelta(minutes=duration_minutes)
        )
    if end_at:
        deadlines.append(parse_utc_timestamp(end_at))
    if not deadlines:
        return None
    attempt_deadline = min(deadlines)
    return max(0, int((attempt_deadline - now).total_seconds()))


def format_vietnam_time(utc_text: str) -> str:
    """Show a stored UTC timestamp in Vietnam time, e.g. '18 Oct 2026, 15:15 (UTC+7)'."""
    return format_vietnam_timestamp(utc_text)


def result_summary(correct: int, total: int) -> dict:
    """US09: 'correct/total' and the percent rounded half-up, e.g. 1/8 -> 13 (not round()'s 12)."""
    # Integer form of floor(correct * 100 / total + 0.5), so no float error creeps in.
    percent = (200 * correct + total) // (2 * total) if total else 0
    return {
        "correct": correct,
        "total": total,
        "fraction": f"{correct}/{total}",
        "percent": percent,
    }


def _check_quiz_can_start(quiz) -> None:
    """BR4: only published quizzes can be started."""
    if quiz is None:
        raise AttemptError(404, errors.QUIZ_NOT_FOUND)
    if quiz["status"] == "closed":
        raise AttemptError(403, errors.QUIZ_CLOSED)
    if quiz["status"] != "published":
        raise AttemptError(403, errors.QUIZ_NOT_PUBLISHED)


def _check_schedule_allows_start(quiz, now: datetime) -> None:
    if quiz["start_at"] and now < parse_utc_timestamp(quiz["start_at"]):
        raise AttemptError(403, "This quiz is not open yet.")
    if quiz["end_at"] and now >= parse_utc_timestamp(quiz["end_at"]):
        raise AttemptError(403, "The scheduled time for this quiz has ended.")


def _attempt_deadline(attempt, quiz) -> datetime | None:
    deadlines = []
    if not quiz["duration_unlimited"]:
        deadlines.append(
            datetime.strptime(attempt["started_at"], TIMESTAMP_FORMAT)
            + timedelta(minutes=quiz["duration_minutes"])
        )
    if quiz["end_at"]:
        deadlines.append(parse_utc_timestamp(quiz["end_at"]))
    return min(deadlines) if deadlines else None


def _finalize(connection, attempt, submitted_at: datetime) -> bool:
    """Store the submission time and score (correct / total questions)."""
    total = len(repo.list_questions_with_choices(connection, attempt["quiz_id"]))
    correct = repo.count_correct_answers(connection, attempt["attempt_id"])
    score = correct / total if total else 0.0
    updated = repo.mark_submitted(
        connection,
        attempt["attempt_id"],
        submitted_at.strftime(TIMESTAMP_FORMAT),
        score,
    )
    return updated == 1


def _auto_submit_if_expired(connection, attempt, quiz) -> None:
    """Submit an attempt whose time is up, stamped at the moment time ran out."""
    deadline = _attempt_deadline(attempt, quiz)
    if deadline is None or _now() < deadline:
        return

    _finalize(connection, attempt, deadline)
    connection.commit()
    raise AutoSubmitted(quiz["quiz_id"])


def _find_open_attempt(connection, student_id: int, quiz_id: int):
    """Return the quiz and the student's open attempt, or raise a friendly error."""
    quiz = repo.get_quiz(connection, quiz_id)
    if quiz is None:
        raise AttemptError(404, errors.QUIZ_NOT_FOUND)

    attempt = repo.get_open_attempt(connection, student_id, quiz_id)
    if attempt is None:
        if repo.count_submitted_attempts(connection, student_id, quiz_id) >= quiz["max_attempts"]:
            raise AttemptError(409, errors.ALREADY_SUBMITTED)
        raise AttemptError(404, errors.ATTEMPT_NOT_STARTED)

    _auto_submit_if_expired(connection, attempt, quiz)
    return quiz, attempt


def _answered_numbers(questions: list[dict], selected: dict) -> list[int]:
    return [
        number
        for number, item in enumerate(questions, start=1)
        if selected.get(item["question_id"]) is not None
    ]


def _review_data(connection, quiz, attempt) -> dict:
    questions = repo.list_questions_with_choices(connection, quiz["quiz_id"])
    selected = repo.get_selected_choices(connection, attempt["attempt_id"])
    answered = _answered_numbers(questions, selected)
    return {
        "quiz": dict(quiz),
        "attempt_id": attempt["attempt_id"],
        "total_questions": len(questions),
        "answered_count": len(answered),
        "unanswered_numbers": [
            number for number in range(1, len(questions) + 1) if number not in answered
        ],
        "remaining_seconds": remaining_seconds(
            attempt["started_at"],
            None if quiz["duration_unlimited"] else quiz["duration_minutes"],
            end_at=quiz["end_at"],
        ),
    }


def start_attempt(db_path: str | Path, student_id: int, quiz_id: int) -> dict:
    """Resume the student's open attempt or create a new one."""
    connection = get_connection(db_path)
    try:
        # Lock before checking so two simultaneous starts cannot both create an attempt.
        close_expired_published_quizzes(
            connection, _now().strftime(TIMESTAMP_FORMAT)
        )
        connection.commit()
        connection.execute("BEGIN IMMEDIATE")
        quiz = repo.get_quiz(connection, quiz_id)
        _check_quiz_can_start(quiz)

        # Only submitted attempts consume the lecturer-configured attempt limit.
        if (
            repo.count_submitted_attempts(connection, student_id, quiz_id)
            >= quiz["max_attempts"]
        ):
            raise AttemptError(409, errors.ALREADY_SUBMITTED)

        attempt = repo.get_open_attempt(connection, student_id, quiz_id)
        if attempt is None:
            _check_schedule_allows_start(quiz, _now())
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
        quiz, attempt = _find_open_attempt(connection, student_id, quiz_id)

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
            "answered_numbers": _answered_numbers(questions, selected),
            "remaining_seconds": remaining_seconds(
                attempt["started_at"],
                None if quiz["duration_unlimited"] else quiz["duration_minutes"],
                end_at=quiz["end_at"],
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

        # A late answer is not saved; the attempt is submitted as it stood at the deadline.
        _auto_submit_if_expired(connection, attempt, repo.get_quiz(connection, quiz_id))
        if not repo.choice_belongs_to_question(connection, choice_id, question_id, quiz_id):
            raise AttemptError(400, errors.INVALID_CHOICE)

        repo.upsert_answer(connection, attempt_id, question_id, choice_id)
        connection.commit()
    finally:
        connection.close()


def get_review_data(db_path: str | Path, student_id: int, quiz_id: int) -> dict:
    """Answered count and unanswered question numbers for the review page."""
    connection = get_connection(db_path)
    try:
        quiz, attempt = _find_open_attempt(connection, student_id, quiz_id)
        return _review_data(connection, quiz, attempt)
    finally:
        connection.close()


def submit_attempt(
    db_path: str | Path,
    student_id: int,
    quiz_id: int,
    attempt_id: int,
    confirmed: bool,
) -> None:
    """Submit the attempt once (BR5, BR6); unanswered questions need confirmation."""
    connection = get_connection(db_path)
    try:
        # Lock so two simultaneous submits cannot both pass the checks below.
        connection.execute("BEGIN IMMEDIATE")
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
        _auto_submit_if_expired(connection, attempt, quiz)

        review = _review_data(connection, quiz, attempt)
        if review["unanswered_numbers"] and not confirmed:
            raise UnansweredNotConfirmed(review)

        if not _finalize(connection, attempt, _now()):
            raise AttemptError(409, errors.ALREADY_SUBMITTED)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def get_submitted_data(db_path: str | Path, student_id: int, quiz_id: int) -> dict:
    """The student's submitted attempt and its result for the confirmation page (US08, US09)."""
    connection = get_connection(db_path)
    try:
        quiz = repo.get_quiz(connection, quiz_id)
        attempt = repo.get_submitted_attempt(connection, student_id, quiz_id)
        if quiz is None or attempt is None:
            raise AttemptError(404, errors.ATTEMPT_NOT_SUBMITTED)
        # Recount from the stored answers, which cannot change after submission (BR6).
        total = len(repo.list_questions_with_choices(connection, quiz_id))
        correct = repo.count_correct_answers(connection, attempt["attempt_id"])
        return {
            "quiz": dict(quiz),
            "submitted_at_display": format_vietnam_time(attempt["submitted_at"]),
            "result": result_summary(correct, total),
        }
    finally:
        connection.close()
