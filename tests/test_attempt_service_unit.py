from __future__ import annotations
"""Isolated unit tests for the US06 take-attempt service."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from src.services import attempt_service


@pytest.fixture
def take_page_service(monkeypatch):
    connection = Mock()
    quiz = {
        "quiz_id": 42,
        "status": "published",
        "duration_unlimited": 0,
        "duration_minutes": 20,
        "end_at": None,
        "max_attempts": 1,
    }
    attempt = {
        "attempt_id": 7,
        "student_id": 3,
        "quiz_id": 42,
        "started_at": "2026-10-26T08:00:00",
        "submitted_at": None,
    }
    questions = [
        {"question_id": number, "content": f"Question {number}"}
        for number in range(1, 11)
    ]
    selected = {3: 203}

    monkeypatch.setattr(attempt_service, "get_connection", lambda _: connection)
    monkeypatch.setattr(attempt_service.repo, "get_quiz", lambda *_: quiz)
    monkeypatch.setattr(attempt_service.repo, "get_open_attempt", lambda *_: attempt)
    monkeypatch.setattr(
        attempt_service.repo, "list_questions_with_choices", lambda *_: questions
    )
    monkeypatch.setattr(
        attempt_service.repo, "get_selected_choices", lambda *_: selected
    )
    monkeypatch.setattr(
        attempt_service,
        "_now",
        lambda: datetime(2026, 10, 26, 8, 8, 0),
    )
    return connection, questions, selected


def test_take_page_returns_one_requested_question_from_ten_question_quiz(
    take_page_service,
):
    _, questions, _ = take_page_service

    for number in range(1, 11):
        data = attempt_service.get_take_page_data("unused", 3, 42, number)

        assert data["question"] == questions[number - 1]
        assert data["question_number"] == number
        assert data["total_questions"] == 10


def test_refreshing_take_page_restores_same_question_answer_and_remaining_time(
    take_page_service,
):
    connection, _, _ = take_page_service

    before_refresh = attempt_service.get_take_page_data("unused", 3, 42, 3)
    after_refresh = attempt_service.get_take_page_data("unused", 3, 42, 3)

    assert after_refresh["attempt_id"] == before_refresh["attempt_id"] == 7
    assert after_refresh["question"] == before_refresh["question"]
    assert after_refresh["selected_choice_id"] == before_refresh["selected_choice_id"] == 203
    assert after_refresh["answered_numbers"] == before_refresh["answered_numbers"] == [3]
    assert after_refresh["remaining_seconds"] == before_refresh["remaining_seconds"] == 12 * 60
    assert connection.close.call_count == 2


def test_take_page_rejects_question_number_outside_ten_question_quiz(
    take_page_service,
):
    for number in (0, 11):
        with pytest.raises(attempt_service.AttemptError) as error:
            attempt_service.get_take_page_data("unused", 3, 42, number)

        assert error.value.status_code == 404


def test_take_page_starts_thirty_minute_timer(take_page_service, monkeypatch):
    _, _, _ = take_page_service
    monkeypatch.setattr(
        attempt_service,
        "_now",
        lambda: datetime(2026, 10, 26, 8, 0, 0),
    )
    quiz = attempt_service.repo.get_quiz(None, 42)
    quiz["duration_minutes"] = 30

    data = attempt_service.get_take_page_data("unused", 3, 42, 1)

    assert data["remaining_seconds"] == 30 * 60


def test_take_page_uses_closing_time_when_it_precedes_duration(take_page_service):
    _, _, _ = take_page_service
    quiz = attempt_service.repo.get_quiz(None, 42)
    quiz["end_at"] = "2026-10-26T08:15:00"

    data = attempt_service.get_take_page_data("unused", 3, 42, 1)

    assert data["remaining_seconds"] == 7 * 60


def test_us13_expiry_boundary_keeps_attempt_open_just_before_deadline(
    take_page_service, monkeypatch
):
    connection, _, _ = take_page_service
    quiz = attempt_service.repo.get_quiz(None, 42)
    finalize = Mock()
    monkeypatch.setattr(attempt_service, "_finalize", finalize)
    monkeypatch.setattr(
        attempt_service, "_now", lambda: datetime(2026, 10, 26, 8, 19, 59)
    )

    attempt_service._auto_submit_if_expired(
        connection,
        {"attempt_id": 7, "started_at": "2026-10-26T08:00:00"},
        quiz,
    )

    finalize.assert_not_called()
    connection.commit.assert_not_called()


def test_us13_expiry_boundary_auto_submits_at_exact_deadline(
    take_page_service, monkeypatch
):
    connection, _, _ = take_page_service
    quiz = attempt_service.repo.get_quiz(None, 42)
    attempt = {"attempt_id": 7, "quiz_id": 42, "started_at": "2026-10-26T08:00:00"}
    finalize = Mock(return_value=True)
    monkeypatch.setattr(attempt_service, "_finalize", finalize)
    monkeypatch.setattr(
        attempt_service, "_now", lambda: datetime(2026, 10, 26, 8, 20, 0)
    )

    with pytest.raises(attempt_service.AutoSubmitted) as error:
        attempt_service._auto_submit_if_expired(connection, attempt, quiz)

    assert error.value.quiz_id == 42
    finalize.assert_called_once_with(connection, attempt, datetime(2026, 10, 26, 8, 20, 0))
    connection.commit.assert_called_once()


def test_us13_second_submit_is_rejected_without_changing_saved_result(monkeypatch):
    connection = Mock()
    attempt = {
        "attempt_id": 7,
        "student_id": 3,
        "quiz_id": 42,
        "submitted_at": "2026-10-26T08:10:00",
        "score": 0.8,
    }
    monkeypatch.setattr(attempt_service, "get_connection", lambda _: connection)
    monkeypatch.setattr(attempt_service.repo, "get_attempt", lambda *_: attempt)
    mark_submitted = Mock()
    monkeypatch.setattr(attempt_service.repo, "mark_submitted", mark_submitted)

    with pytest.raises(attempt_service.AttemptError) as error:
        attempt_service.submit_attempt("unused", 3, 42, 7, confirmed=True)

    assert error.value.status_code == 409
    assert str(error.value) == attempt_service.errors.ALREADY_SUBMITTED
    mark_submitted.assert_not_called()
    connection.rollback.assert_called_once()
    connection.close.assert_called_once()


def test_expired_attempt_is_auto_submitted_at_earliest_deadline(
    take_page_service, monkeypatch
):
    connection, questions, _ = take_page_service
    quiz = attempt_service.repo.get_quiz(None, 42)
    quiz["end_at"] = "2026-10-26T08:15:00"
    monkeypatch.setattr(
        attempt_service,
        "_now",
        lambda: datetime(2026, 10, 26, 8, 15, 0),
    )
    monkeypatch.setattr(attempt_service.repo, "count_correct_answers", lambda *_: 1)
    marked = Mock(return_value=1)
    monkeypatch.setattr(attempt_service.repo, "mark_submitted", marked)

    with pytest.raises(attempt_service.AutoSubmitted) as error:
        attempt_service.get_take_page_data("unused", 3, 42, 3)

    assert error.value.quiz_id == 42
    marked.assert_called_once_with(
        connection, 7, "2026-10-26T08:15:00", pytest.approx(0.1)
    )
    connection.commit.assert_called_once()


def test_review_reports_zero_unanswered_when_all_ten_questions_are_answered(
    take_page_service, monkeypatch
):
    _, questions, selected = take_page_service
    selected.clear()
    selected.update(
        {
            question["question_id"]: 100 + question["question_id"]
            for question in questions
        }
    )

    review = attempt_service.get_review_data("unused", 3, 42)

    assert review["total_questions"] == 10
    assert review["answered_count"] == 10
    assert review["unanswered_numbers"] == []


@pytest.fixture
def start_attempt_service(monkeypatch):
    connection = Mock()
    quiz = {
        "quiz_id": 42,
        "status": "published",
        "start_at": None,
        "end_at": None,
        "max_attempts": 2,
    }
    attempt = {
        "attempt_id": 7,
        "student_id": 3,
        "quiz_id": 42,
        "started_at": "2026-10-26T08:00:00",
        "submitted_at": None,
    }
    monkeypatch.setattr(attempt_service, "get_connection", lambda _: connection)
    monkeypatch.setattr(
        attempt_service, "_now", lambda: datetime(2026, 10, 26, 8, 0, 0)
    )
    monkeypatch.setattr(
        attempt_service,
        "close_expired_published_quizzes",
        Mock(return_value=0),
    )
    monkeypatch.setattr(attempt_service.repo, "get_quiz", lambda *_: quiz)
    monkeypatch.setattr(attempt_service.repo, "count_submitted_attempts", lambda *_: 0)
    monkeypatch.setattr(attempt_service.repo, "get_open_attempt", lambda *_: attempt)
    return connection, quiz, attempt


def test_start_attempt_resumes_existing_open_attempt(start_attempt_service, monkeypatch):
    _, _, attempt = start_attempt_service
    create_attempt = Mock()
    monkeypatch.setattr(attempt_service.repo, "create_attempt", create_attempt)

    result = attempt_service.start_attempt("unused", 3, 42)

    assert result == attempt
    create_attempt.assert_not_called()


def test_start_attempt_rejects_unpublished_quiz(start_attempt_service):
    _, quiz, _ = start_attempt_service
    quiz["status"] = "draft"

    with pytest.raises(attempt_service.AttemptError) as error:
        attempt_service.start_attempt("unused", 3, 42)

    assert error.value.status_code == 403


def test_start_attempt_rejects_when_br5_attempt_limit_is_reached(
    start_attempt_service, monkeypatch
):
    connection, _, _ = start_attempt_service
    monkeypatch.setattr(attempt_service.repo, "count_submitted_attempts", lambda *_: 2)

    with pytest.raises(attempt_service.AttemptError) as error:
        attempt_service.start_attempt("unused", 3, 42)

    assert error.value.status_code == 409
    connection.rollback.assert_called_once()


@pytest.mark.parametrize(
    ("start_at", "end_at", "now"),
    [
        ("2026-10-26T08:05:00", None, datetime(2026, 10, 26, 8, 0, 0)),
        (None, "2026-10-26T08:00:00", datetime(2026, 10, 26, 8, 0, 0)),
    ],
)
def test_start_attempt_rejects_outside_quiz_schedule(
    start_attempt_service, monkeypatch, start_at, end_at, now
):
    connection, quiz, _ = start_attempt_service
    quiz["start_at"] = start_at
    quiz["end_at"] = end_at
    monkeypatch.setattr(attempt_service, "_now", lambda: now)
    monkeypatch.setattr(attempt_service.repo, "get_open_attempt", lambda *_: None)

    with pytest.raises(attempt_service.AttemptError) as error:
        attempt_service.start_attempt("unused", 3, 42)

    assert error.value.status_code == 403
    connection.rollback.assert_called_once()
