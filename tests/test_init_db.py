import sqlite3

import pytest
from werkzeug.security import check_password_hash

from src.db import get_connection
from src.init_db import init_db


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
    return path


def test_init_db_seeds_expected_rows(db_path):
    with get_connection(db_path) as connection:
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("user", "quiz", "question", "choice", "attempt", "answer")
        }

    assert counts == {
        "user": 7,
        "quiz": 15,
        "question": 15,
        "choice": 60,
        "attempt": 0,
        "answer": 0,
    }


def test_init_db_is_repeatable(db_path):
    assert init_db(db_path) == {
        "user": 7,
        "quiz": 15,
        "question": 15,
        "choice": 60,
        "attempt": 0,
        "answer": 0,
    }


def test_quiz_requires_positive_duration(db_path):
    with (
        get_connection(db_path) as connection,
        pytest.raises(sqlite3.IntegrityError),
    ):
        connection.execute(
            "INSERT INTO quiz (lecturer_id, title, duration_minutes) "
            "VALUES (1, 'Invalid duration', 0)"
        )


def test_question_cannot_have_two_correct_choices(db_path):
    with (
        get_connection(db_path) as connection,
        pytest.raises(sqlite3.IntegrityError),
    ):
        connection.execute(
            "INSERT INTO choice (question_id, content, is_correct) "
            "VALUES (1, 'Another correct answer', 1)"
        )


def test_connection_enables_foreign_keys(db_path):
    with get_connection(db_path) as connection:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO quiz (lecturer_id, title, duration_minutes) "
                "VALUES (999, 'Invalid owner', 10)"
            )


def test_seed_has_login_accounts_and_a_closed_quiz(db_path):
    with get_connection(db_path) as connection:
        lecturer = connection.execute(
            "SELECT password_hash, role FROM user WHERE email = ?",
            ("ngan.lecturer@example.edu",),
        ).fetchone()
        student = connection.execute(
            "SELECT password_hash, role FROM user WHERE email = ?",
            ("duc.student@example.edu",),
        ).fetchone()
        closed_quizzes = connection.execute(
            "SELECT COUNT(*) FROM quiz WHERE status = 'closed'"
        ).fetchone()[0]

    assert lecturer["role"] == "lecturer"
    assert student["role"] == "student"
    assert check_password_hash(lecturer["password_hash"], "MiniLMS2026!")
    assert check_password_hash(student["password_hash"], "MiniLMS2026!")
    assert closed_quizzes == 1
