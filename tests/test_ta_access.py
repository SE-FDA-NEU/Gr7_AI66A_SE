"""TA (teaching assistant) can read attempts and audit history, but cannot write."""
from __future__ import annotations

from contextlib import closing

import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

PASSWORD = "MiniLMS2026!"
TA_EMAIL = "mai.ta@example.edu"


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    # Attempt 1 belongs to student 3 on quiz 1, which lecturer Ngan (id 1) owns.
    with closing(get_connection(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO attempt (attempt_id, student_id, quiz_id, started_at)
            VALUES (1, 3, 1, '2026-10-27T08:00:00')
            """
        )
        conn.commit()
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


def login(client, email):
    client.post("/logout")
    return client.post("/login", data={"email": email, "password": PASSWORD})


def test_ta_login_redirects_to_dashboard(client):
    response = login(client, TA_EMAIL)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/lecturer/dashboard")
    with client.session_transaction() as user_session:
        assert user_session["role"] == "ta"


def test_ta_wrong_password_is_still_rejected(client):
    response = client.post(
        "/login", data={"email": TA_EMAIL, "password": "wrong-password"}
    )

    assert response.status_code == 401


def test_ta_dashboard_lists_all_quizzes_without_write_actions(client):
    login(client, TA_EMAIL)

    response = client.get("/lecturer/dashboard")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "All Quizzes" in page
    assert "Introduction to Software Engineering" in page  # owned by Ngan
    assert "Create Quiz" not in page
    assert "Manage Quiz" not in page


def test_lecturer_dashboard_is_unchanged(client):
    login(client, "ngan.lecturer@example.edu")

    page = client.get("/lecturer/dashboard").get_data(as_text=True)

    assert "My Quizzes" in page
    assert "Create Quiz" in page
    assert "Manage Quiz" in page


@pytest.mark.parametrize(
    "url",
    [
        "/lecturer/quiz/1/attempts",
        "/lecturer/quiz/1/attempts/1",
        "/lecturer/quiz/1/attempts/1/audit",
    ],
)
def test_ta_can_read_attempts_of_a_quiz_it_does_not_own(client, url):
    login(client, TA_EMAIL)

    assert client.get(url).status_code == 200


def test_ta_attempt_pages_hide_the_quiz_management_link(client):
    login(client, TA_EMAIL)

    page = client.get("/lecturer/quiz/1/attempts").get_data(as_text=True)

    assert "Quiz details" not in page


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/quiz/create"),
        ("post", "/quiz/create"),
        ("get", "/lecturer/quiz/1/publish"),
        ("post", "/lecturer/quiz/1/publish"),
        ("post", "/lecturer/quiz/1/close"),
        ("post", "/lecturer/quiz/1/schedule"),
        ("post", "/quiz/1/questions"),
        ("post", "/quiz/1/questions/1/edit"),
        ("get", "/student/dashboard"),
        ("post", "/student/quiz/1/start"),
    ],
)
def test_ta_cannot_write_or_use_student_pages(client, method, url):
    login(client, TA_EMAIL)

    response = getattr(client, method)(url)

    assert response.status_code == 403

def test_ta_can_view_quiz_statistics(client, TA_EMAIL):
    login(client, TA_EMAIL)

    response = client.get("/lecturer/quiz/1/statistics")

    assert response.status_code == 200

def test_other_lecturer_still_cannot_read_audit_of_a_quiz_it_does_not_own(client):
    login(client, "nam.lecturer@example.edu")  # does not own quiz 1

    assert client.get("/lecturer/quiz/1/attempts/1/audit").status_code == 403
    assert client.get("/lecturer/quiz/1/attempts").status_code == 403


def test_student_still_cannot_read_audit(client):
    login(client, "duc.student@example.edu")

    assert client.get("/lecturer/quiz/1/attempts/1/audit").status_code == 403