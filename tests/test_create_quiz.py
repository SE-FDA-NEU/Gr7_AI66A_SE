
import sqlite3
import pytest

from src.app import create_app


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "us02_quizzes.db"

    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE user (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            );

            CREATE TABLE quiz (
                quiz_id INTEGER PRIMARY KEY,
                lecturer_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                duration_minutes INTEGER NOT NULL
                    CHECK (duration_minutes > 0),
                duration_unlimited INTEGER NOT NULL DEFAULT 0,
                start_at TEXT,
                end_at TEXT
            );

            INSERT INTO user
                (user_id, name, email, password_hash, role)
            VALUES
                (1, 'Test Lecturer', 'lecturer@test.com',
                 'test_hash', 'lecturer'),
                (2, 'Test Student', 'student@test.com',
                 'test_hash', 'student');
            """
        )

    return path


@pytest.fixture
def client(db_path):
    app = create_app({
        "TESTING": True,
        "DATABASE_PATH": str(db_path),
        "SECRET_KEY": "us02-test-secret",
    })
    return app.test_client()


def login_as(client, user_id, role):
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = role
        session["name"] = "Test User"


def get_quizzes(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM quiz ORDER BY quiz_id"
        ).fetchall()

    return [dict(row) for row in rows]


def post_quiz(client, **overrides):
    form = {
        "title": "Test Quiz",
        "description": "",
        "duration": "30",
    }
    form.update(overrides)

    return client.post(
        "/quiz/create",
        data=form,
        follow_redirects=False,
    )


def test_us02_01_create_quiz_as_draft(client, db_path):
    login_as(client, 1, "lecturer")

    response = post_quiz(
        client,
        title="Midterm Quiz 1",
        description="Week 5 review",
    )

    quizzes = get_quizzes(db_path)

    assert response.status_code == 302
    assert len(quizzes) == 1
    assert quizzes[0]["title"] == "Midterm Quiz 1"
    assert quizzes[0]["description"] == "Week 5 review"
    assert quizzes[0]["status"] == "draft"
    assert quizzes[0]["lecturer_id"] == 1


def test_us02_02_store_duration_30(client, db_path):
    login_as(client, 1, "lecturer")

    response = post_quiz(client, duration="30")
    quizzes = get_quizzes(db_path)

    assert response.status_code == 302
    assert len(quizzes) == 1
    assert quizzes[0]["duration_minutes"] == 30


def test_us02_03_reject_empty_title(client, db_path):
    login_as(client, 1, "lecturer")

    response = post_quiz(client, title="")

    assert response.status_code == 422
    assert b"Quiz title is required." in response.data
    assert len(get_quizzes(db_path)) == 0


def test_us02_04_reject_whitespace_title(client, db_path):
    login_as(client, 1, "lecturer")

    response = post_quiz(client, title="   ")

    assert response.status_code == 422
    assert b"Quiz title is required." in response.data
    assert len(get_quizzes(db_path)) == 0


def test_us02_05_reject_duration_zero(client, db_path):
    login_as(client, 1, "lecturer")

    response = post_quiz(client, duration="0")

    assert response.status_code == 422
    assert b"Duration must be a positive number." in response.data
    assert len(get_quizzes(db_path)) == 0


def test_us02_06_accept_duration_one(client, db_path):
    login_as(client, 1, "lecturer")

    response = post_quiz(client, duration="1")
    quizzes = get_quizzes(db_path)

    assert response.status_code == 302
    assert len(quizzes) == 1
    assert quizzes[0]["duration_minutes"] == 1
    assert quizzes[0]["status"] == "draft"


def test_us02_07_reject_negative_duration(client, db_path):
    login_as(client, 1, "lecturer")

    response = post_quiz(client, duration="-1")

    assert response.status_code == 422
    assert b"Duration must be a positive number." in response.data
    assert len(get_quizzes(db_path)) == 0


def test_us02_08_student_cannot_create_quiz(client, db_path):
    login_as(client, 2, "student")

    response = post_quiz(
        client,
        title="Unauthorized Quiz",
    )

    assert response.status_code == 403
    assert len(get_quizzes(db_path)) == 0
