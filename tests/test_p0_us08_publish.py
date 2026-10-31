"""US08 submission tests required by issue #137."""
from __future__ import annotations

import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

QUIZ_ID = 1
STUDENT_ID = 3


@pytest.fixture
def db_path(tmp_path):
    """Create a seeded test database with a quiz that is currently available."""
    path = tmp_path / "minilms_test.db"
    init_db(path)
    with get_connection(path) as connection:
        connection.execute("UPDATE quiz SET start_at = NULL, end_at = NULL")
    return path


@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": str(db_path)})
    return app.test_client()


def login_student(client):
    response = client.post(
        "/login",
        data={"email": "duc.student@example.edu", "password": "MiniLMS2026!"},
    )
    assert response.status_code == 302


def start_attempt(client, db_path):
    response = client.post(f"/student/quiz/{QUIZ_ID}/start")
    assert response.status_code == 302
    with get_connection(db_path) as connection:
        return connection.execute(
            "SELECT attempt_id FROM attempt "
            "WHERE student_id = ? AND quiz_id = ? AND submitted_at IS NULL",
            (STUDENT_ID, QUIZ_ID),
        ).fetchone()[0]


def submit(client, attempt_id, confirm=False):
    data = {"attempt_id": attempt_id}
    if confirm:
        data["confirm"] = "yes"
    return client.post(f"/student/quiz/{QUIZ_ID}/submit", data=data)


def get_attempt_state(db_path, attempt_id):
    with get_connection(db_path) as connection:
        attempt = connection.execute(
            "SELECT submitted_at, score FROM attempt WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchone()
        answers = connection.execute(
            "SELECT question_id, choice_id FROM answer "
            "WHERE attempt_id = ? ORDER BY question_id",
            (attempt_id,),
        ).fetchall()
    return tuple(attempt), [tuple(answer) for answer in answers]


def answer_seed_question(client, db_path, attempt_id):
    with get_connection(db_path) as connection:
        question_id, choice_id = connection.execute(
            "SELECT q.question_id, c.choice_id FROM question q "
            "JOIN choice c ON c.question_id = q.question_id "
            "WHERE q.quiz_id = ? ORDER BY q.position, c.choice_id LIMIT 1",
            (QUIZ_ID,),
        ).fetchone()

    response = client.post(
        f"/student/quiz/{QUIZ_ID}/take",
        data={
            "attempt_id": attempt_id,
            "question_id": question_id,
            "choice_id": choice_id,
            "go": "review",
        },
    )
    assert response.status_code == 302


def test_us08_02_submit_unanswered_requires_confirmation(client, db_path):
    # US08-02: requesting submission with an unanswered question requires confirmation.
    login_student(client)
    attempt_id = start_attempt(client, db_path)

    response = submit(client, attempt_id)
    html = response.get_data(as_text=True)

    assert response.status_code == 422
    assert "Question 1" in html
    assert 'name="confirm"' in html
    assert "Some questions are still unanswered" in html
    assert get_attempt_state(db_path, attempt_id) == ((None, None), [])


def test_us08_03_confirmed_unanswered_submission_scores_zero(client, db_path):
    # US08-03: confirming submission with unanswered questions submits and scores them zero.
    login_student(client)
    attempt_id = start_attempt(client, db_path)

    response = submit(client, attempt_id, confirm=True)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        f"/student/quiz/{QUIZ_ID}/submitted"
    )
    submitted_at, score = get_attempt_state(db_path, attempt_id)[0]
    assert submitted_at is not None
    assert score == 0.0
    result_page = client.get(response.headers["Location"])
    assert result_page.status_code == 200
    assert "Score: 0/1 (0%)" in result_page.get_data(as_text=True)


def test_us08_04_second_submission_is_rejected_without_changing_data(client, db_path):
    # US08-04: a second submission is rejected and the first submission stays unchanged.
    login_student(client)
    attempt_id = start_attempt(client, db_path)
    answer_seed_question(client, db_path, attempt_id)

    first_response = submit(client, attempt_id)
    assert first_response.status_code == 302
    state_after_first_submission = get_attempt_state(db_path, attempt_id)
    assert state_after_first_submission[0][0] is not None

    second_response = submit(client, attempt_id, confirm=True)

    assert second_response.status_code == 409
    assert "You have no attempts remaining for this quiz." in second_response.get_data(
        as_text=True
    )
    assert get_attempt_state(db_path, attempt_id) == state_after_first_submission
    with get_connection(db_path) as connection:
        submitted_count = connection.execute(
            "SELECT COUNT(*) FROM attempt "
            "WHERE student_id = ? AND quiz_id = ? AND submitted_at IS NOT NULL",
            (STUDENT_ID, QUIZ_ID),
        ).fetchone()[0]
    assert submitted_count == 1
