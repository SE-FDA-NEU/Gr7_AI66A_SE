"""US08 submission tests required by issue #137."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import src.services.attempt_service as attempt_service
from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

QUIZ_ID = 1
STUDENT_ID = 3
OTHER_STUDENT_EMAIL = "lan.student@example.edu"
START = datetime(2026, 10, 31, 8, 0, 0)  # fixed clock: tests never depend on today's date


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


# --------------------------------------------------------------------------
# Helpers for the test cases below that need their own quiz or a fixed clock.
# --------------------------------------------------------------------------
def make_quiz(db_path, n_questions, duration_minutes=30):
    """Insert a published quiz; in every question the first choice is correct."""
    with get_connection(db_path) as connection:
        lecturer_id = connection.execute(
            "SELECT user_id FROM user WHERE role = 'lecturer' LIMIT 1"
        ).fetchone()[0]
        quiz_id = connection.execute(
            "INSERT INTO quiz (lecturer_id, title, status, duration_minutes, max_attempts) "
            "VALUES (?, ?, 'published', ?, 1)",
            (lecturer_id, f"US08 quiz {n_questions} questions", duration_minutes),
        ).lastrowid
        for position in range(1, n_questions + 1):
            question_id = connection.execute(
                "INSERT INTO question (quiz_id, content, points, position) VALUES (?, ?, 1, ?)",
                (quiz_id, f"Question {position}?", position),
            ).lastrowid
            connection.executemany(
                "INSERT INTO choice (question_id, content, is_correct) VALUES (?, ?, ?)",
                [(question_id, f"Option {n}", int(n == 1)) for n in range(1, 5)],
            )
    return quiz_id


def question_choices(db_path, quiz_id):
    """Return [(question_id, [choice_id, ...]), ...] in question order."""
    with get_connection(db_path) as connection:
        questions = connection.execute(
            "SELECT question_id FROM question WHERE quiz_id = ? ORDER BY position", (quiz_id,)
        ).fetchall()
        return [
            (
                q[0],
                [
                    c[0]
                    for c in connection.execute(
                        "SELECT choice_id FROM choice WHERE question_id = ? ORDER BY choice_id",
                        (q[0],),
                    )
                ],
            )
            for q in questions
        ]


def start_quiz(client, db_path, quiz_id):
    assert client.post(f"/student/quiz/{quiz_id}/start").status_code == 302
    with get_connection(db_path) as connection:
        return connection.execute(
            "SELECT attempt_id FROM attempt WHERE quiz_id = ? AND submitted_at IS NULL",
            (quiz_id,),
        ).fetchone()[0]


def post_answer(client, quiz_id, attempt_id, question_id, choice_id):
    return client.post(
        f"/student/quiz/{quiz_id}/take",
        data={
            "attempt_id": attempt_id,
            "question_id": question_id,
            "choice_id": choice_id,
            "go": "review",
        },
    )


def stored_answers(db_path, attempt_id):
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT question_id, choice_id FROM answer WHERE attempt_id = ? ORDER BY question_id",
            (attempt_id,),
        ).fetchall()
    return [tuple(row) for row in rows]


def submitted_attempt_count(db_path, quiz_id):
    with get_connection(db_path) as connection:
        return connection.execute(
            "SELECT COUNT(*) FROM attempt WHERE quiz_id = ? AND submitted_at IS NOT NULL",
            (quiz_id,),
        ).fetchone()[0]


# --------------------------------------------------------------------------
# Test cases US08-01, US08-05, US08-06, US08-07
# --------------------------------------------------------------------------
def test_us08_01_all_ten_questions_answered_is_submitted_once(client, db_path):
    # US08-01 | normal: 10 of 10 questions answered, the student submits.
    quiz_id = make_quiz(db_path, n_questions=10)
    login_student(client)
    attempt_id = start_quiz(client, db_path, quiz_id)
    for question_id, choice_ids in question_choices(db_path, quiz_id):
        assert post_answer(client, quiz_id, attempt_id, question_id, choice_ids[0]).status_code == 302

    response = client.post(f"/student/quiz/{quiz_id}/submit", data={"attempt_id": attempt_id})

    assert response.status_code == 302  # no confirmation needed: nothing is unanswered
    assert response.headers["Location"].endswith(f"/student/quiz/{quiz_id}/submitted")
    with get_connection(db_path) as connection:
        submitted_at, score = connection.execute(
            "SELECT submitted_at, score FROM attempt WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()
    assert submitted_at is not None
    assert score == 1.0
    assert submitted_attempt_count(db_path, quiz_id) == 1
    assert len(stored_answers(db_path, attempt_id)) == 10
    result_page = client.get(response.headers["Location"])
    assert "Score: 10/10 (100%)" in result_page.get_data(as_text=True)


def test_us08_05_answer_cannot_be_changed_after_submission(client, db_path):
    # US08-05 | error (BR6): changing an answer after the attempt was submitted is refused.
    login_student(client)
    attempt_id = start_attempt(client, db_path)
    answer_seed_question(client, db_path, attempt_id)
    assert submit(client, attempt_id).status_code == 302
    state_after_submission = get_attempt_state(db_path, attempt_id)
    question_id, first_choice = stored_answers(db_path, attempt_id)[0]
    other_choice = question_choices(db_path, QUIZ_ID)[0][1][1]
    assert other_choice != first_choice

    response = post_answer(client, QUIZ_ID, attempt_id, question_id, other_choice)

    assert response.status_code == 409
    assert get_attempt_state(db_path, attempt_id) == state_after_submission
    assert stored_answers(db_path, attempt_id) == [(question_id, first_choice)]


@pytest.mark.parametrize(
    ("elapsed", "auto_submitted"),
    [
        (timedelta(minutes=29, seconds=59), False),  # just below the limit
        (timedelta(minutes=30, seconds=1), True),    # just above the limit
    ],
    ids=["29:59", "30:01"],
)
def test_us08_06_submission_around_the_30_minute_limit(
    client, db_path, monkeypatch, elapsed, auto_submitted
):
    # US08-06 | boundary, both sides of the 30-minute time limit.
    quiz_id = make_quiz(db_path, n_questions=1, duration_minutes=30)
    login_student(client)
    monkeypatch.setattr(attempt_service, "_now", lambda: START)
    attempt_id = start_quiz(client, db_path, quiz_id)
    question_id, choice_ids = question_choices(db_path, quiz_id)[0]
    assert post_answer(client, quiz_id, attempt_id, question_id, choice_ids[0]).status_code == 302

    monkeypatch.setattr(attempt_service, "_now", lambda: START + elapsed)
    if auto_submitted:
        # A late answer is not saved; the attempt is closed at the deadline (30:00).
        response = post_answer(client, quiz_id, attempt_id, question_id, choice_ids[1])
        expected_submitted_at = START + timedelta(minutes=30)
        assert response.status_code == 302
        assert response.headers["Location"].endswith(f"/student/quiz/{quiz_id}/submitted?timeout=1")
    else:
        # Still inside the limit: a normal submission, stamped with the real time.
        response = client.post(f"/student/quiz/{quiz_id}/submit", data={"attempt_id": attempt_id})
        expected_submitted_at = START + elapsed
        assert response.status_code == 302
        assert response.headers["Location"].endswith(f"/student/quiz/{quiz_id}/submitted")

    with get_connection(db_path) as connection:
        submitted_at = connection.execute(
            "SELECT submitted_at FROM attempt WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()[0]
    assert submitted_at == expected_submitted_at.strftime("%Y-%m-%dT%H:%M:%S")
    assert stored_answers(db_path, attempt_id) == [(question_id, choice_ids[0])]  # late answer not saved
    assert submitted_attempt_count(db_path, quiz_id) == 1


def test_us08_07_another_student_cannot_submit_this_attempt(client, db_path):
    # US08-07 | error: a different student tries to submit someone else's attempt.
    login_student(client)  # Duc starts an attempt
    attempt_id = start_attempt(client, db_path)
    state_before = get_attempt_state(db_path, attempt_id)
    client.post("/logout")
    login = client.post(
        "/login", data={"email": OTHER_STUDENT_EMAIL, "password": "MiniLMS2026!"}
    )
    assert login.status_code == 302

    response = submit(client, attempt_id, confirm=True)

    assert response.status_code == 403
    assert get_attempt_state(db_path, attempt_id) == state_before == ((None, None), [])