import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db


@pytest.fixture
def auth_client(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


def test_login_page_is_available(auth_client):
    response = auth_client.get("/login")

    assert response.status_code == 200
    assert "Sign in to Mini LMS" in response.get_data(as_text=True)


@pytest.mark.parametrize(
    ("email", "role", "destination", "page_heading"),
    [
        (
            "ngan.lecturer@example.edu",
            "lecturer",
            "/lecturer/dashboard",
            "Lecturer dashboard",
        ),
        (
            "duc.student@example.edu",
            "student",
            "/student/dashboard",
            "Available quizzes",
        ),
    ],
)
def test_login_redirects_to_the_users_role_dashboard(
    auth_client,
    email,
    role,
    destination,
    page_heading,
):
    response = auth_client.post(
        "/login",
        data={"email": email, "password": "MiniLMS2026!"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(destination)
    with auth_client.session_transaction() as user_session:
        assert user_session["role"] == role

    dashboard = auth_client.get(destination)
    assert dashboard.status_code == 200
    assert page_heading in dashboard.get_data(as_text=True)


def test_missing_login_fields_show_a_shared_bad_request_message(auth_client):
    response = auth_client.post("/login", data={"email": ""})

    assert response.status_code == 400
    assert "Email and password are required." in response.get_data(as_text=True)


def test_invalid_password_shows_a_friendly_unauthorized_message(auth_client):
    response = auth_client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "incorrect",
        },
    )

    assert response.status_code == 401
    assert "Incorrect email or password." in response.get_data(as_text=True)


def test_fifth_failed_login_locks_account_for_15_minutes(auth_client, monkeypatch):
    import src.auth as auth_module

    now = 1_800_000_000
    monkeypatch.setattr(auth_module.time, "time", lambda: now)
    for attempt in range(5):
        response = auth_client.post(
            "/login",
            data={
                "email": "duc.student@example.edu",
                "password": f"incorrect-{attempt}",
            },
        )

    assert response.status_code == 429
    assert (
        "Too many failed attempts. Try again in 15 minutes."
        in response.get_data(as_text=True)
    )
    with get_connection(auth_client.application.config["DATABASE_PATH"]) as connection:
        locked_until = connection.execute(
            "SELECT locked_until FROM login_lockout WHERE email = ?",
            ("duc.student@example.edu",),
        ).fetchone()[0]
    assert locked_until == now + 15 * 60

    response = auth_client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "MiniLMS2026!",
        },
    )
    assert response.status_code == 429

    monkeypatch.setattr(auth_module.time, "time", lambda: now + 15 * 60 - 1)
    response = auth_client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "MiniLMS2026!",
        },
    )
    assert response.status_code == 429

    monkeypatch.setattr(auth_module.time, "time", lambda: now + 15 * 60)
    response = auth_client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "MiniLMS2026!",
        },
    )
    assert response.status_code == 302


def test_login_attempts_outside_the_10_minute_window_do_not_lock_account(
    auth_client,
    monkeypatch,
):
    import src.auth as auth_module

    now = 1_800_000_000
    monkeypatch.setattr(auth_module.time, "time", lambda: now)
    for _ in range(4):
        auth_client.post(
            "/login",
            data={
                "email": "duc.student@example.edu",
                "password": "incorrect",
            },
        )

    monkeypatch.setattr(auth_module.time, "time", lambda: now + 10 * 60 + 1)
    response = auth_client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "incorrect",
        },
    )

    assert response.status_code == 401
    with get_connection(auth_client.application.config["DATABASE_PATH"]) as connection:
        failure_count = connection.execute(
            "SELECT COUNT(*) FROM login_failure WHERE email = ?",
            ("duc.student@example.edu",),
        ).fetchone()[0]
    assert failure_count == 1


def test_user_without_the_required_role_gets_friendly_403(auth_client):
    auth_client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "MiniLMS2026!",
        },
    )

    response = auth_client.get("/lecturer/dashboard")

    assert response.status_code == 403
    assert (
        "You do not have permission to access this page."
        in response.get_data(as_text=True)
    )


def test_unauthenticated_dashboard_redirects_to_login(auth_client):
    response = auth_client.get("/student/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_logout_clears_session_and_redirects_to_login(auth_client):
    auth_client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "MiniLMS2026!",
        },
    )

    dashboard = auth_client.get("/student/dashboard")
    assert b'data-confirm="Are you sure you want to sign out?"' in dashboard.data

    response = auth_client.post("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert auth_client.get("/student/dashboard").headers["Location"].endswith(
        "/login"
    )
