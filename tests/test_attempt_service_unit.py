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
