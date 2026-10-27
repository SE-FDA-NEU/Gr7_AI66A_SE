from __future__ import annotations
import sqlite3

from src.app import create_app


def test_index(client):
    response = client.get('/')
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

def test_health(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_index_redirects_signed_in_users_to_their_dashboard(client):
    with client.session_transaction() as session:
        session["user_id"] = 3
        session["role"] = "student"

    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert client.get(response.headers["Location"]).status_code == 302


def test_app_migrates_legacy_quiz_table_without_losing_rows(tmp_path):
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE quiz (
                quiz_id INTEGER PRIMARY KEY,
                duration_minutes INTEGER NOT NULL
            )
            """
        )
        connection.execute(
            "INSERT INTO quiz (quiz_id, duration_minutes) VALUES (1, 20)"
        )

    create_app({"TESTING": True, "DATABASE_PATH": db_path})

    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT duration_minutes, duration_unlimited FROM quiz WHERE quiz_id = 1"
        ).fetchone()
        columns = {
            column[1] for column in connection.execute("PRAGMA table_info(quiz)")
        }

    assert row == (20, 0)
    assert {"max_attempts", "last_published_end_at", "closed_by_deadline"} <= columns


def test_app_migrates_attempt_limit_and_drops_single_submission_index(tmp_path):
    from src.db import get_connection
    from src.init_db import init_db

    db_path = tmp_path / "attempt-limit-migration.db"
    init_db(db_path)
    with get_connection(db_path) as connection:
        connection.execute(
            """
            CREATE UNIQUE INDEX one_submitted_attempt_per_student_quiz
            ON attempt(student_id, quiz_id) WHERE submitted_at IS NOT NULL
            """
        )

    create_app({"TESTING": True, "DATABASE_PATH": db_path})

    with get_connection(db_path) as connection:
        index = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'index' "
            "AND name = 'one_submitted_attempt_per_student_quiz'"
        ).fetchone()
        maximum = connection.execute(
            "SELECT max_attempts FROM quiz WHERE quiz_id = 1"
        ).fetchone()[0]

    assert index is None
    assert maximum == 1