from datetime import datetime, timedelta

import pytest

import src.services.attempt_service as attempt_service
from src.errors import AUTO_SUBMITTED
from tests.test_attempt import (
    PUBLISHED_QUIZ,
    client,
    db_path,
    login,
    multi_question_client,
    shows_message,
    start_and_answer,
    submit,
)

# US09: student sees an automatically calculated result.
# Expected values come from the US09 acceptance criteria and docs/ui.md
# (percent = score x 100 rounded half-up), not from the code's output.

SUBMITTED_PAGE = f"/student/quiz/{PUBLISHED_QUIZ}/submitted"


@pytest.mark.parametrize(
    ("correct", "total", "fraction", "percent"),
    [
        (10, 10, "10/10", 100),  # US09-01 all correct, upper boundary
        (8, 10, "8/10", 80),  # US09-02 partly correct (AC1)
        (0, 10, "0/10", 0),  # US09-03 all wrong, lower boundary
        (2, 3, "2/3", 67),  # US09-04 66.67 rounds up, not truncated to 66
        (1, 3, "1/3", 33),  # US09-05 33.33 rounds down
        (1, 8, "1/8", 13),  # US09-06 12.5 rounds half-up, not to even (12)
        (0, 0, "0/0", 0),  # US09-07 quiz without questions, no division by zero
    ],
)
def test_result_summary(correct, total, fraction, percent):
    """US09-01..07: correct / total is shown as a fraction and a rounded percent."""
    assert attempt_service.result_summary(correct, total) == {
        "correct": correct,
        "total": total,
        "fraction": fraction,
        "percent": percent,
    }


def test_submitted_page_shows_score(client, db_path):
    """US09-09 (AC1): Given a submitted attempt with 1 of 1 correct,
    when the student opens the result, then the page shows 1/1 and 100%."""
    start_and_answer(client, db_path, {1: 0})  # first choice is the correct one
    submit(client, db_path)

    first = client.get(SUBMITTED_PAGE)
    second = client.get(SUBMITTED_PAGE)

    assert first.status_code == 200
    assert "Score: 1/1 (100%)" in first.get_data(as_text=True)
    # BR6: opening the result again shows the same score.
    assert "Score: 1/1 (100%)" in second.get_data(as_text=True)


def test_unanswered_attempt_scores_zero(multi_question_client, db_path):
    """US09-08: Given no question is answered and submission is confirmed,
    when the student opens the result, then the page shows 0/3 and 0%."""
    client = multi_question_client
    start_and_answer(client, db_path, {})
    submit(client, db_path, confirm=True)

    assert "Score: 0/3 (0%)" in client.get(SUBMITTED_PAGE).get_data(as_text=True)


def test_auto_submitted_attempt_shows_score(multi_question_client, db_path, monkeypatch):
    """US09-10: Given 2 of 3 answers are correct and time runs out,
    when the student is sent to the result, then it shows the auto-submit notice, 2/3 and 67%."""
    client = multi_question_client
    start = datetime(2026, 10, 18, 8, 0, 0)
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    start_and_answer(client, db_path, {1: 0, 2: 1, 3: 0})  # Q2 wrong

    # Quiz 1 lasts 20 minutes.
    monkeypatch.setattr(attempt_service, "_now", lambda: start + timedelta(minutes=20))
    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")

    assert response.headers["Location"].endswith(f"{SUBMITTED_PAGE}?timeout=1")
    result = client.get(response.headers["Location"])
    assert shows_message(result, AUTO_SUBMITTED)
    assert "Score: 2/3 (67%)" in result.get_data(as_text=True)


# Decision table for GET /student/quiz/:id/submitted (docs/testing.md, US09)


def test_unsubmitted_attempt_shows_no_score(client, db_path):
    """US09-11 / R2 (AC4): Given the attempt has not been submitted,
    when the student opens the result route, then no final score is displayed."""
    start_and_answer(client, db_path, {1: 0})

    response = client.get(SUBMITTED_PAGE)

    assert response.status_code == 404
    assert "Score:" not in response.get_data(as_text=True)


def test_other_students_result_is_not_visible(client, db_path):
    """US09-12 / R3: Given only Duc has submitted quiz 1,
    when Lan opens the result route, then she gets 404 and never sees Duc's score."""
    start_and_answer(client, db_path, {1: 0})
    submit(client, db_path)
    client.post("/logout")
    login(client, "lan.student@example.edu")

    response = client.get(SUBMITTED_PAGE)

    assert response.status_code == 404
    assert "Score:" not in response.get_data(as_text=True)


def test_lecturer_cannot_open_result(client):
    """US09-13 / R4 (BR1): a lecturer gets 403 on the student result route."""
    login(client, "ngan.lecturer@example.edu")

    assert client.get(SUBMITTED_PAGE).status_code == 403


def test_guest_result_redirects_to_login(client):
    """US09-14 / R5 (BR1): a guest is redirected to /login."""
    response = client.get(SUBMITTED_PAGE)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
