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

    assert row == (20, 0)