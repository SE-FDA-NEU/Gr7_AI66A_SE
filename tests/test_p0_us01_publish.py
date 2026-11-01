"""US01 sign-in, lockout, and role-separation acceptance tests."""
from __future__ import annotations

import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

PASSWORD = "MiniLMS2026!"
STUDENT_EMAIL = "duc.student@example.edu"
LECTURER_EMAIL = "ngan.lecturer@example.edu"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "us01.db"
    init_db(path)
    return path


@pytest.fixture
def client(db_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE_PATH": str(db_path),
            "SECRET_KEY": "test-only-secret",
        }
    )
    return app.test_client()


def sign_in(client, email, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def test_us01_01_lecturer_sign_in_redirects_to_lecturer_dashboard(client):
    # US01-01: a lecturer with valid credentials reaches the lecturer dashboard.
    response = sign_in(client, LECTURER_EMAIL)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/lecturer/dashboard")
    with client.session_transaction() as user_session:
        assert user_session["role"] == "lecturer"


def test_us01_02_student_sign_in_redirects_to_student_dashboard(client):
    # US01-02: a student with valid credentials reaches the student dashboard.
    response = sign_in(client, STUDENT_EMAIL)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/dashboard")
    with client.session_transaction() as user_session:
        assert user_session["role"] == "student"


def test_us01_03_first_wrong_password_does_not_lock_account(client, db_path):
    # US01-03: the first incorrect password shows an error without locking the account.
    response = sign_in(client, STUDENT_EMAIL, "incorrect")

    assert response.status_code == 401
    assert "Incorrect email or password." in response.get_data(as_text=True)
    with get_connection(db_path) as connection:
        failure_count = connection.execute(
            "SELECT COUNT(*) FROM login_failure WHERE email = ?",
            (STUDENT_EMAIL,),
        ).fetchone()[0]
        lockout_count = connection.execute(
            "SELECT COUNT(*) FROM login_lockout WHERE email = ?",
            (STUDENT_EMAIL,),
        ).fetchone()[0]
    assert failure_count == 1
    assert lockout_count == 0


def test_us01_04_four_recent_failures_allow_correct_password(
    client, db_path, monkeypatch
):
    # US01-04: four failed attempts in the rolling window remain below the lockout limit.
    import src.auth as auth_module

    now = 1_800_000_000
    monkeypatch.setattr(auth_module.time, "time", lambda: now)
    for _ in range(4):
        assert sign_in(client, STUDENT_EMAIL, "incorrect").status_code == 401

    response = sign_in(client, STUDENT_EMAIL)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/dashboard")
    with get_connection(db_path) as connection:
        failure_count = connection.execute(
            "SELECT COUNT(*) FROM login_failure WHERE email = ?",
            (STUDENT_EMAIL,),
        ).fetchone()[0]
    assert failure_count == 0


def test_us01_05_fifth_recent_failure_locks_account(client, db_path, monkeypatch):
    # US01-05: the fifth failed attempt in ten minutes locks the account for fifteen minutes.
    import src.auth as auth_module

    now = 1_800_000_000
    monkeypatch.setattr(auth_module.time, "time", lambda: now)
    for _ in range(4):
        assert sign_in(client, STUDENT_EMAIL, "incorrect").status_code == 401

    response = sign_in(client, STUDENT_EMAIL, "incorrect")

    assert response.status_code == 429
    assert "Too many failed attempts. Try again in 15 minutes." in response.get_data(
        as_text=True
    )
    with get_connection(db_path) as connection:
        locked_until = connection.execute(
            "SELECT locked_until FROM login_lockout WHERE email = ?",
            (STUDENT_EMAIL,),
        ).fetchone()[0]
    assert locked_until == now + 15 * 60
    assert sign_in(client, STUDENT_EMAIL).status_code == 429


def test_us01_06_failure_older_than_ten_minutes_is_excluded(
    client, db_path, monkeypatch
):
    # US01-06: an older failed attempt is removed from the rolling ten-minute count.
    import src.auth as auth_module

    now = 1_800_000_000
    monkeypatch.setattr(auth_module.time, "time", lambda: now)
    for _ in range(4):
        assert sign_in(client, STUDENT_EMAIL, "incorrect").status_code == 401

    monkeypatch.setattr(auth_module.time, "time", lambda: now + 10 * 60 + 1)
    response = sign_in(client, STUDENT_EMAIL, "incorrect")

    assert response.status_code == 401
    with get_connection(db_path) as connection:
        failure_count = connection.execute(
            "SELECT COUNT(*) FROM login_failure WHERE email = ?",
            (STUDENT_EMAIL,),
        ).fetchone()[0]
        lockout_count = connection.execute(
            "SELECT COUNT(*) FROM login_lockout WHERE email = ?",
            (STUDENT_EMAIL,),
        ).fetchone()[0]
    assert failure_count == 1
    assert lockout_count == 0


def test_us01_07_lockout_expires_after_fifteen_minutes(client, monkeypatch):
    # US01-07: login is blocked before expiry and allowed after the fifteen-minute lockout.
    import src.auth as auth_module

    now = 1_800_000_000
    monkeypatch.setattr(auth_module.time, "time", lambda: now)
    for _ in range(5):
        response = sign_in(client, STUDENT_EMAIL, "incorrect")
    assert response.status_code == 429

    monkeypatch.setattr(auth_module.time, "time", lambda: now + 15 * 60 - 1)
    assert sign_in(client, STUDENT_EMAIL).status_code == 429

    monkeypatch.setattr(auth_module.time, "time", lambda: now + 15 * 60 + 1)
    response = sign_in(client, STUDENT_EMAIL)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/dashboard")


def test_us01_08_student_and_guest_cannot_access_lecturer_create_page(client):
    # US01-08: lecturer-only access rejects a student and redirects a guest to sign-in.
    student_response = sign_in(client, STUDENT_EMAIL)
    assert student_response.status_code == 302
    assert client.get("/quiz/create").status_code == 403

    client.post("/logout")
    guest_response = client.get("/student/dashboard")
    assert guest_response.status_code == 302
    assert guest_response.headers["Location"].endswith("/login")


def test_us01_09_lecturer_cannot_add_questions_to_another_lecturers_quiz(
    client, db_path
):
    # US01-09: a lecturer cannot edit a quiz owned by another lecturer.
    with get_connection(db_path) as connection:
        owner_id = connection.execute(
            "SELECT user_id FROM user WHERE email = ?",
            (LECTURER_EMAIL,),
        ).fetchone()[0]
        quiz_id = connection.execute(
            "INSERT INTO quiz (lecturer_id, title, duration_minutes) "
            "VALUES (?, ?, ?)",
            (owner_id, "US01 ownership test", 30),
        ).lastrowid
        connection.commit()

    sign_in(client, "nam.lecturer@example.edu")
    response = client.post(
        f"/quiz/{quiz_id}/questions",
        data={
            "content": "Question?",
            "choices": ["One", "Two", "Three", "Four"],
            "correct_index": "0",
            "points": "1",
        },
    )

    assert response.status_code == 403
    assert (
        "You do not have permission to edit this quiz."
        in response.get_data(as_text=True)
    )
    with get_connection(db_path) as connection:
        question_count = connection.execute(
            "SELECT COUNT(*) FROM question WHERE quiz_id = ?",
            (quiz_id,),
        ).fetchone()[0]
    assert question_count == 0
