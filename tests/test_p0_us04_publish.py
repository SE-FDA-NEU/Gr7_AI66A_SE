"""Milestone 4 - P0 story US04: Lecturer publishes and closes a quiz.

Test case IDs US04-01 .. US04-08 are documented in docs/testing.md (Section 2.4).
Each ID appears in the name of exactly one test and in a comment on its first line.

Isolation rules for this file:
  * every test uses its own temporary SQLite file (tmp_path); data/minilms.db is never read;
  * the quizzes under test are created here, so the tests do not depend on the seed data;
  * quiz start/end times are cleared, so the result never depends on today's date.
"""
from __future__ import annotations

import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

PASSWORD = "MiniLMS2026!"
NGAN = "ngan.lecturer@example.edu"   # lecturer, owns the quizzes created below
NAM = "nam.lecturer@example.edu"     # another lecturer
DUC = "duc.student@example.edu"      # student
DUC_ID = 3
NGAN_ID = 1

NO_QUESTIONS_MESSAGE = "A quiz must contain at least 1 question."
NO_CORRECT_MESSAGE = "Please select one correct option."


# ---------------------------------------------------------------- fixtures
@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
    with get_connection(path) as connection:
        # No schedule: results must not depend on the date the tests are run.
        connection.execute("UPDATE quiz SET start_at = NULL, end_at = NULL")
        connection.commit()
    return path


@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


# ----------------------------------------------------------------- helpers
def login(client, email):
    client.post("/logout")
    response = client.post("/login", data={"email": email, "password": PASSWORD})
    assert response.status_code == 302


def make_quiz(
    db_path,
    questions: int,
    status: str = "draft",
    correct_per_question: int = 1,
    lecturer_id: int = NGAN_ID,
) -> int:
    """Insert a quiz owned by `lecturer_id` with `questions` four-choice questions.

    `correct_per_question` is how many of the 4 choices are marked correct
    (1 = valid question, 0 = question without a correct answer).
    """
    with get_connection(db_path) as connection:
        quiz_id = connection.execute(
            "INSERT INTO quiz (lecturer_id, title, status, duration_minutes) VALUES (?, ?, ?, ?)",
            (lecturer_id, f"US04 quiz with {questions} questions", status, 30),
        ).lastrowid
        for position in range(1, questions + 1):
            question_id = connection.execute(
                "INSERT INTO question (quiz_id, content, points, position) VALUES (?, ?, 1, ?)",
                (quiz_id, f"Question {position}?", position),
            ).lastrowid
            for index in range(1, 5):
                connection.execute(
                    "INSERT INTO choice (question_id, content, is_correct) VALUES (?, ?, ?)",
                    (question_id, f"Option {index}", int(index <= correct_per_question)),
                )
        connection.commit()
    return quiz_id


def quiz_status(db_path, quiz_id) -> str:
    with get_connection(db_path) as connection:
        return connection.execute(
            "SELECT status FROM quiz WHERE quiz_id = ?", (quiz_id,)
        ).fetchone()[0]


def count(db_path, sql, params=()) -> int:
    with get_connection(db_path) as connection:
        return connection.execute(sql, params).fetchone()[0]


# ------------------------------------------------------------ test cases
def test_us04_01_quiz_with_10_valid_questions_is_published(client, db_path):
    # US04-01 | normal
    quiz_id = make_quiz(db_path, questions=10)
    login(client, NGAN)

    response = client.post(f"/lecturer/quiz/{quiz_id}/publish", follow_redirects=True)

    assert response.status_code == 200
    assert "Quiz published successfully." in response.get_data(as_text=True)
    assert quiz_status(db_path, quiz_id) == "published"


def test_us04_02_quiz_with_exactly_1_valid_question_can_be_published(client, db_path):
    # US04-02 | boundary, on the limit (the smallest quiz that may be published)
    quiz_id = make_quiz(db_path, questions=1)
    login(client, NGAN)

    response = client.post(f"/lecturer/quiz/{quiz_id}/publish", follow_redirects=True)

    assert response.status_code == 200
    assert quiz_status(db_path, quiz_id) == "published"


def test_us04_03_quiz_with_0_questions_cannot_be_published(client, db_path):
    # US04-03 | boundary, just below the limit
    quiz_id = make_quiz(db_path, questions=0)
    login(client, NGAN)

    response = client.post(f"/lecturer/quiz/{quiz_id}/publish")

    assert response.status_code == 422
    assert NO_QUESTIONS_MESSAGE in response.get_data(as_text=True)
    assert quiz_status(db_path, quiz_id) == "draft"


def test_us04_04_question_without_a_correct_choice_blocks_publishing(client, db_path):
    # US04-04 | error (BR3)
    quiz_id = make_quiz(db_path, questions=1, correct_per_question=0)
    login(client, NGAN)

    response = client.post(f"/lecturer/quiz/{quiz_id}/publish")

    assert response.status_code == 422
    assert NO_CORRECT_MESSAGE in response.get_data(as_text=True)
    assert quiz_status(db_path, quiz_id) == "draft"


def test_us04_05_student_cannot_start_a_closed_quiz(client, db_path):
    # US04-05 | error
    quiz_id = make_quiz(db_path, questions=1, status="closed")
    login(client, DUC)

    response = client.post(f"/student/quiz/{quiz_id}/start")

    assert response.status_code == 403
    assert "This quiz is closed" in response.get_data(as_text=True)
    assert count(db_path, "SELECT COUNT(*) FROM attempt WHERE quiz_id = ?", (quiz_id,)) == 0


def test_us04_06_closing_a_quiz_keeps_submitted_attempts(client, db_path):
    # US04-06 | normal
    quiz_id = make_quiz(db_path, questions=1, status="published")
    with get_connection(db_path) as connection:
        attempt_id = connection.execute(
            "INSERT INTO attempt (student_id, quiz_id, started_at, submitted_at, score) "
            "VALUES (?, ?, '2026-10-18T09:00:00', '2026-10-18T09:15:00', 9.5)",
            (DUC_ID, quiz_id),
        ).lastrowid
        connection.commit()
    login(client, NGAN)

    close = client.post(f"/lecturer/quiz/{quiz_id}/close")
    assert close.status_code in (200, 302)
    assert quiz_status(db_path, quiz_id) == "closed"

    # The submitted attempt is unchanged and the lecturer can still open the list.
    with get_connection(db_path) as connection:
        attempt = connection.execute(
            "SELECT submitted_at, score FROM attempt WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()
    assert tuple(attempt) == ("2026-10-18T09:15:00", 9.5)
    assert client.get(f"/lecturer/quiz/{quiz_id}/attempts").status_code == 200


def test_us04_07_another_lecturer_cannot_publish_the_quiz(client, db_path):
    # US04-07 | error (BR2)
    quiz_id = make_quiz(db_path, questions=1)
    login(client, NAM)

    response = client.post(f"/lecturer/quiz/{quiz_id}/publish")

    assert response.status_code == 403
    assert quiz_status(db_path, quiz_id) == "draft"


def test_us04_08_publishing_an_already_published_quiz_is_refused(client, db_path):
    # US04-08 | error
    quiz_id = make_quiz(db_path, questions=1, status="published")
    login(client, NGAN)

    response = client.post(f"/lecturer/quiz/{quiz_id}/publish")

    assert response.status_code == 409
    assert quiz_status(db_path, quiz_id) == "published"