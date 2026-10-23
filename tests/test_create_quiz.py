
import sqlite3

import pytest

from src.app import create_app
from src.repositories.quiz_repository import create_quiz
from src.services.quiz_service import InvalidQuiz, create_new_quiz


# ==========================================
# TEST DATABASE
# ==========================================

@pytest.fixture
def test_db(tmp_path):
    db_path = tmp_path / "test_quiz.db"

    conn = sqlite3.connect(db_path)

    conn.executescript("""
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
            duration_unlimited INTEGER NOT NULL DEFAULT 0
                CHECK (duration_unlimited IN (0, 1)),
            start_at TEXT,
            end_at TEXT
        );

        INSERT INTO user (
            user_id, name, email, password_hash, role
        )
        VALUES (
            1, 'Test Lecturer', 'lecturer@test.com',
            'test_hash', 'lecturer'
        );

        INSERT INTO user (
            user_id, name, email, password_hash, role
        )
        VALUES (
            2, 'Test Student', 'student@test.com',
            'test_hash', 'student'
        );
    """)

    conn.commit()
    conn.close()

    return db_path


@pytest.fixture
def client(test_db):
    app = create_app({
        "TESTING": True,
        "DATABASE_PATH": str(test_db),
        "SECRET_KEY": "test-only-secret",
    })

    return app.test_client()


def login_as(client, user_id, role):
    """Set up a test session without using the login form."""
    with client.session_transaction() as session:
        session["user_id"] = user_id
        session["role"] = role
        session["name"] = "Test User"


# ==========================================
# SERVICE TESTS
# ==========================================

def test_create_quiz_success(test_db):
    quiz_id = create_new_quiz(
        test_db,
        lecturer_id=1,
        title="Midterm Quiz 1",
        duration="30",
    )

    conn = sqlite3.connect(test_db)

    quiz = conn.execute(
        """
        SELECT title, status, duration_minutes, duration_unlimited, lecturer_id, start_at, end_at
        FROM quiz
        WHERE quiz_id = ?
        """,
        (quiz_id,),
    ).fetchone()

    conn.close()

    assert quiz == (
        "Midterm Quiz 1",
        "draft",
        30,
        0,
        1,
        None,
        None,
    )


def test_create_quiz_empty_title(test_db):
    with pytest.raises(
        InvalidQuiz,
        match="Quiz title is required.",
    ):
        create_new_quiz(
            test_db,
            lecturer_id=1,
            title="",
            duration="30",
        )


def test_create_quiz_whitespace_title(test_db):
    with pytest.raises(
        InvalidQuiz,
        match="Quiz title is required.",
    ):
        create_new_quiz(
            test_db,
            lecturer_id=1,
            title="   ",
            duration="30",
        )


@pytest.mark.parametrize(
    "duration",
    ["0", "-5", "abc", ""],
)
def test_create_quiz_invalid_duration(test_db, duration):
    with pytest.raises(
        InvalidQuiz,
        match="Duration must be a positive number.",
    ):
        create_new_quiz(
            test_db,
            lecturer_id=1,
            title="Test Quiz",
            duration=duration,
        )


def test_create_quiz_title_is_trimmed(test_db):
    quiz_id = create_new_quiz(
        test_db,
        lecturer_id=1,
        title="  Software Engineering  ",
        duration="45",
    )

    conn = sqlite3.connect(test_db)

    title = conn.execute(
        "SELECT title FROM quiz WHERE quiz_id = ?",
        (quiz_id,),
    ).fetchone()[0]

    conn.close()

    assert title == "Software Engineering"


def test_create_quiz_converts_hanoi_schedule_to_utc(test_db):
    quiz_id = create_new_quiz(
        test_db,
        lecturer_id=1,
        title="Scheduled Quiz",
        duration="60",
        start_at="2026-10-20T11:00",
        end_at="2026-10-20T12:00",
    )
    with sqlite3.connect(test_db) as connection:
        schedule = connection.execute(
            "SELECT start_at, end_at FROM quiz WHERE quiz_id = ?",
            (quiz_id,),
        ).fetchone()

    assert schedule == ("2026-10-20T04:00:00", "2026-10-20T05:00:00")


def test_create_quiz_can_have_unlimited_duration_and_only_a_start_time(test_db):
    quiz_id = create_new_quiz(
        test_db,
        lecturer_id=1,
        title="Open-ended Quiz",
        duration="",
        start_at="2026-10-20T11:00",
        duration_unlimited=True,
    )
    with sqlite3.connect(test_db) as connection:
        settings = connection.execute(
            """
            SELECT duration_unlimited, start_at, end_at
            FROM quiz WHERE quiz_id = ?
            """,
            (quiz_id,),
        ).fetchone()

    assert settings == (1, "2026-10-20T04:00:00", None)


@pytest.mark.parametrize(
    ("start_at", "end_at", "message"),
    [
        ("2026-10-20T12:00", "2026-10-20T11:00", "end time must be later"),
        ("not-a-time", "2026-10-20T12:00", "Enter valid start and end times"),
    ],
)
def test_create_quiz_rejects_invalid_schedule(test_db, start_at, end_at, message):
    with pytest.raises(InvalidQuiz, match=message):
        create_new_quiz(
            test_db,
            lecturer_id=1,
            title="Scheduled Quiz",
            duration="60",
            start_at=start_at,
            end_at=end_at,
        )


# ==========================================
# ROUTE TESTS
# ==========================================

def test_create_quiz_routes_registered(client):
    rules = {
        (rule.rule, method)
        for rule in client.application.url_map.iter_rules()
        for method in rule.methods
    }

    assert ("/quiz/create", "GET") in rules
    assert ("/quiz/create", "POST") in rules


def test_guest_redirected_to_login(client):
    response = client.get("/quiz/create")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_guest_cannot_submit_quiz(client):
    response = client.post(
        "/quiz/create",
        data={"title": "Test Quiz", "duration": "30"},
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_lecturer_can_open_create_quiz(client):
    login_as(client, 1, "lecturer")

    response = client.get("/quiz/create")

    assert response.status_code == 200
    assert b"Create New Quiz" in response.data
    assert b'data-confirm="Are you sure you want to create this quiz?"' in response.data
    assert b'name="title"' in response.data
    assert b'name="start_at"' in response.data
    assert b'name="end_at"' in response.data
    assert b'name="duration_unlimited"' in response.data
    assert b'required' in response.data


def test_student_cannot_open_create_quiz(client):
    login_as(client, 2, "student")

    response = client.get("/quiz/create")

    assert response.status_code == 403


def test_student_cannot_create_quiz(client):
    login_as(client, 2, "student")

    response = client.post(
        "/quiz/create",
        data={"title": "Unauthorized Quiz", "duration": "30"},
    )

    assert response.status_code == 403


def test_lecturer_create_quiz_post_success(client, test_db):
    login_as(client, 1, "lecturer")

    response = client.post(
        "/quiz/create",
        data={
            "title": "Midterm Quiz 1",
            "duration": "30",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302

    conn = sqlite3.connect(test_db)

    quiz = conn.execute(
        """
        SELECT quiz_id, title, status,
               duration_minutes, lecturer_id
        FROM quiz
        WHERE title = ?
        """,
        ("Midterm Quiz 1",),
    ).fetchone()

    conn.close()

    assert quiz is not None
    assert quiz[1:] == ("Midterm Quiz 1", "draft", 30, 1)

    assert f"/lecturer/quiz/{quiz[0]}/publish" in response.headers["Location"]


def test_lecturer_can_create_quiz_without_a_time_limit(client, test_db):
    login_as(client, 1, "lecturer")

    response = client.post(
        "/quiz/create",
        data={
            "title": "Unlimited Quiz",
            "duration_unlimited": "yes",
            "start_at": "2026-10-23T11:00",
        },
    )

    assert response.status_code == 302
    with sqlite3.connect(test_db) as connection:
        quiz = connection.execute(
            """
            SELECT duration_unlimited, start_at, end_at
            FROM quiz WHERE title = ?
            """,
            ("Unlimited Quiz",),
        ).fetchone()
    assert quiz == (1, "2026-10-23T04:00:00", None)
    with client.session_transaction() as session:
        assert ("success", "Quiz created successfully.") in session["_flashes"]


def test_lecturer_create_quiz_missing_title(client, test_db):
    login_as(client, 1, "lecturer")

    response = client.post(
        "/quiz/create",
        data={
            "title": "",
            "duration": "30",
        },
    )

    assert response.status_code == 422
    assert b"Quiz title is required." in response.data

    conn = sqlite3.connect(test_db)
    count = conn.execute(
        "SELECT COUNT(*) FROM quiz"
    ).fetchone()[0]
    conn.close()

    assert count == 0


def test_lecturer_create_quiz_invalid_duration(client):
    login_as(client, 1, "lecturer")

    response = client.post(
        "/quiz/create",
        data={
            "title": "Test Quiz",
            "duration": "0",
        },
    )

    assert response.status_code == 422
    assert b"Duration must be a positive number." in response.data


def test_create_quiz_with_description(test_db):
    quiz_id = create_new_quiz(
        test_db,
        lecturer_id=1,
        title="Midterm Quiz 1",
        duration="30",
        description="Week 5 review",
    )
    with sqlite3.connect(test_db) as conn:
        quiz = conn.execute(
            """
            SELECT title, description, status, duration_minutes
            FROM quiz
            WHERE quiz_id = ?
            """,
            (quiz_id,),
        ).fetchone()
    assert quiz == (
        "Midterm Quiz 1",
        "Week 5 review",
        "draft",
        30,
    )


def test_post_create_quiz_saves_description(client, test_db):
    login_as(client, 1, "lecturer")

    response = client.post(
        "/quiz/create",
        data={
            "title": "Midterm Quiz 1",
            "description": "Week 5 review",
            "duration": "30",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    with sqlite3.connect(test_db) as conn:
        quiz = conn.execute(
            "SELECT description FROM quiz WHERE title = ?",
            ("Midterm Quiz 1",),
        ).fetchone()
    assert quiz == ("Week 5 review",)


def test_create_quiz_form_error_preserves_description(client):
    login_as(client, 1, "lecturer")

    response = client.post(
        "/quiz/create",
        data={
            "title": "",
            "description": "Week 5 review",
            "duration": "30",
        },
    )

    assert response.status_code == 422
    assert b' name="description"' in response.data
    assert b"Week 5 review" in response.data
