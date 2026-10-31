from __future__ import annotations

from datetime import datetime, timedelta
import re

import pytest

import src.services.attempt_service as attempt_service
from src.app import create_app
from src.db import get_connection
from src.init_db import init_db


STUDENT_EMAIL = "duc.student@example.edu"
STUDENT_PASSWORD = "MiniLMS2026!"
START = datetime(2026, 10, 31, 8, 0, 0)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
    with get_connection(path) as connection:
        connection.execute("UPDATE quiz SET start_at = NULL, end_at = NULL")
    return path


@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


def make_published_quiz(db_path, n_questions, duration_minutes, max_attempts):
    with get_connection(db_path) as connection:
        lecturer_id = connection.execute(
            "SELECT user_id FROM user WHERE role = 'lecturer' LIMIT 1"
        ).fetchone()["user_id"]
        quiz_id = connection.execute(
            """
            INSERT INTO quiz (
                lecturer_id, title, status, duration_minutes, max_attempts
            )
            VALUES (?, ?, 'published', ?, ?)
            """,
            (
                lecturer_id,
                f"US06 quiz {n_questions}-{duration_minutes}-{max_attempts}",
                duration_minutes,
                max_attempts,
            ),
        ).lastrowid

        for position in range(1, n_questions + 1):
            question_id = connection.execute(
                """
                INSERT INTO question (quiz_id, content, points, position)
                VALUES (?, ?, 1, ?)
                """,
                (quiz_id, f"Question {position}?", position),
            ).lastrowid
            connection.executemany(
                "INSERT INTO choice (question_id, content, is_correct) VALUES (?, ?, ?)",
                [
                    (question_id, f"Option {letter}", int(index == 0))
                    for index, letter in enumerate(("A", "B", "C", "D"))
                ],
            )

    return quiz_id


def login(client):
    response = client.post(
        "/login",
        data={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD},
    )
    assert response.status_code == 302


def get_attempt(db_path, quiz_id):
    with get_connection(db_path) as connection:
        return connection.execute(
            """
            SELECT attempt_id, started_at, submitted_at
            FROM attempt
            WHERE quiz_id = ?
            ORDER BY attempt_id DESC
            LIMIT 1
            """,
            (quiz_id,),
        ).fetchone()


def get_question_and_choice(db_path, quiz_id, position, letter):
    with get_connection(db_path) as connection:
        question = connection.execute(
            "SELECT question_id FROM question WHERE quiz_id = ? AND position = ?",
            (quiz_id, position),
        ).fetchone()
        choice = connection.execute(
            "SELECT choice_id FROM choice WHERE question_id = ? AND content = ?",
            (question["question_id"], f"Option {letter}"),
        ).fetchone()
    return question["question_id"], choice["choice_id"]


def test_us06_01_start_attempt_shows_first_question(client, db_path):
    # US06-01 | normal
    login(client)
    quiz_id = make_published_quiz(db_path, 10, 30, 1)

    started = client.post(f"/student/quiz/{quiz_id}/start")
    assert started.status_code == 302

    page = client.get(f"/student/quiz/{quiz_id}/take?q=1")

    assert page.status_code == 200
    assert "Question 1?" in page.get_data(as_text=True)


def test_us06_02_thirty_minute_quiz_starts_with_1800_seconds(
    client, db_path, monkeypatch
):
    # US06-02 | normal
    login(client)
    quiz_id = make_published_quiz(db_path, 1, 30, 1)
    monkeypatch.setattr(attempt_service, "_now", lambda: START)

    started = client.post(f"/student/quiz/{quiz_id}/start")
    assert started.status_code == 302
    page = client.get(f"/student/quiz/{quiz_id}/take?q=1")

    assert page.status_code == 200
    match = re.search(r'data-remaining="(\d+)"', page.get_data(as_text=True))
    assert match is not None
    assert int(match.group(1)) == 1800


def test_us06_03_saved_choice_remains_selected_after_navigation(client, db_path):
    # US06-03 | normal
    login(client)
    quiz_id = make_published_quiz(db_path, 10, 30, 1)
    assert client.post(f"/student/quiz/{quiz_id}/start").status_code == 302
    question_id, choice_b_id = get_question_and_choice(db_path, quiz_id, 3, "B")
    attempt_id = get_attempt(db_path, quiz_id)["attempt_id"]

    saved = client.post(
        f"/student/quiz/{quiz_id}/take",
        data={
            "attempt_id": attempt_id,
            "question_id": question_id,
            "choice_id": choice_b_id,
            "go": "4",
        },
    )
    assert saved.status_code == 302
    assert client.get(f"/student/quiz/{quiz_id}/take?q=4").status_code == 200

    question_three = client.get(f"/student/quiz/{quiz_id}/take?q=3")

    assert question_three.status_code == 200
    assert re.search(
        rf'<input type="radio" name="choice_id" value="{choice_b_id}"\s+checked>',
        question_three.get_data(as_text=True),
    )


def test_us06_04_get_twice_keeps_question_and_started_at(client, db_path):
    # US06-04 | normal
    login(client)
    quiz_id = make_published_quiz(db_path, 2, 30, 1)
    assert client.post(f"/student/quiz/{quiz_id}/start").status_code == 302

    first_page = client.get(f"/student/quiz/{quiz_id}/take?q=2")
    first_attempt = get_attempt(db_path, quiz_id)
    second_page = client.get(f"/student/quiz/{quiz_id}/take?q=2")
    second_attempt = get_attempt(db_path, quiz_id)

    assert first_page.status_code == 200
    assert second_page.status_code == 200
    assert "Question 2 / 2" in first_page.get_data(as_text=True)
    assert "Question 2 / 2" in second_page.get_data(as_text=True)
    assert first_attempt["attempt_id"] == second_attempt["attempt_id"]
    assert first_attempt["started_at"] == second_attempt["started_at"]


def test_us06_05_question_number_boundaries(client, db_path):
    # US06-05 | boundary
    login(client)
    quiz_id = make_published_quiz(db_path, 10, 30, 1)
    assert client.post(f"/student/quiz/{quiz_id}/start").status_code == 302

    for question_number in (0, 11):
        response = client.get(
            f"/student/quiz/{quiz_id}/take?q={question_number}"
        )
        assert response.status_code == 404

    for question_number in (1, 10):
        response = client.get(
            f"/student/quiz/{quiz_id}/take?q={question_number}"
        )
        assert response.status_code == 200


@pytest.mark.parametrize(
    ("elapsed", "expected_status", "expected_submitted_at"),
    [
        (timedelta(minutes=29, seconds=59), 200, None),
        (timedelta(minutes=30), 302, START + timedelta(minutes=30)),
        (timedelta(minutes=30, seconds=1), 302, START + timedelta(minutes=30)),
    ],
    ids=["29:59", "30:00", "30:01"],
)
def test_us06_06_attempt_expiration_at_time(
    client, db_path, monkeypatch, elapsed, expected_status, expected_submitted_at
):
    # US06-06 | boundary
    login(client)
    quiz_id = make_published_quiz(db_path, 1, 30, 1)
    monkeypatch.setattr(attempt_service, "_now", lambda: START)
    started = client.post(f"/student/quiz/{quiz_id}/start")
    assert started.status_code == 302

    monkeypatch.setattr(attempt_service, "_now", lambda: START + elapsed)
    response = client.get(f"/student/quiz/{quiz_id}/take?q=1")

    assert response.status_code == expected_status
    attempt = get_attempt(db_path, quiz_id)
    if expected_submitted_at is None:
        assert response.get_data(as_text=True).find("Question 1?") >= 0
        assert attempt["submitted_at"] is None
    else:
        assert response.headers["Location"].endswith(
            f"/student/quiz/{quiz_id}/submitted?timeout=1"
        )
        # _auto_submit_if_expired returns only while _now() < deadline; equality expires.
        assert attempt["submitted_at"] == expected_submitted_at.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )


def test_us06_07_draft_and_closed_quizzes_do_not_create_attempts(client, db_path):
    # US06-07 | error
    login(client)
    quiz_id = make_published_quiz(db_path, 1, 30, 1)

    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET status = 'draft' WHERE quiz_id = ?", (quiz_id,)
        )
    draft_response = client.post(f"/student/quiz/{quiz_id}/start")
    assert draft_response.status_code == 403
    with get_connection(db_path) as connection:
        draft_attempt_count = connection.execute(
            "SELECT COUNT(*) FROM attempt WHERE quiz_id = ?", (quiz_id,)
        ).fetchone()[0]
    assert draft_attempt_count == 0

    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET status = 'closed' WHERE quiz_id = ?", (quiz_id,)
        )
    closed_response = client.post(f"/student/quiz/{quiz_id}/start")
    assert closed_response.status_code == 403
    with get_connection(db_path) as connection:
        closed_attempt_count = connection.execute(
            "SELECT COUNT(*) FROM attempt WHERE quiz_id = ?", (quiz_id,)
        ).fetchone()[0]
    assert closed_attempt_count == 0


def test_us06_08_max_attempts_counts_only_submitted_attempts(
    client, db_path, monkeypatch
):
    # US06-08 | boundary
    login(client)
    quiz_id = make_published_quiz(db_path, 1, 30, 2)
    monkeypatch.setattr(attempt_service, "_now", lambda: START)

    for _ in range(2):
        started = client.post(f"/student/quiz/{quiz_id}/start")
        assert started.status_code == 302
        attempt_id = get_attempt(db_path, quiz_id)["attempt_id"]
        submitted = client.post(
            f"/student/quiz/{quiz_id}/submit",
            data={"attempt_id": attempt_id, "confirm": "yes"},
        )
        assert submitted.status_code == 302

    third_start = client.post(f"/student/quiz/{quiz_id}/start")

    assert third_start.status_code == 409
    with get_connection(db_path) as connection:
        attempts = connection.execute(
            "SELECT COUNT(*) FROM attempt WHERE quiz_id = ?", (quiz_id,)
        ).fetchone()[0]
        submitted_attempts = connection.execute(
            """
            SELECT COUNT(*) FROM attempt
            WHERE quiz_id = ? AND submitted_at IS NOT NULL
            """,
            (quiz_id,),
        ).fetchone()[0]
    assert attempts == 2
    assert submitted_attempts == 2
