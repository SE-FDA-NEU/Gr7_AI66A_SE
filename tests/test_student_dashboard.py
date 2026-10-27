from src.app import create_app
from src.init_db import init_db


def test_student_dashboard_has_all_four_ui_states(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    login = client.post(
        "/login",
        data={
            "email": "duc.student@example.edu",
            "password": "MiniLMS2026!",
        },
    )
    response = client.get("/student/dashboard")
    html = response.get_data(as_text=True)

    assert login.status_code == 302
    assert login.headers["Location"].endswith("/student/dashboard")
    assert response.status_code == 200
    assert "Available quizzes" in html
    assert "Duc (student)" in html

    # Loading is visible first; the other three wait for the API response.
    assert '<section id="state-loading" class="state">' in html
    assert "Loading quizzes..." in html
    assert 'id="state-empty" class="state state-empty" hidden' in html
    assert "No quizzes are open for you yet." in html
    assert "New quizzes appear here as soon as your lecturer publishes them." in html
    assert "Refresh" in html
    assert 'id="state-error" class="state state-error" role="alert" hidden' in html
    assert "We can't reach the server." in html
    assert "Your quizzes could not be loaded. Check your connection and try again." in html
    assert "Try again" in html
    assert '<section id="state-data" hidden>' in html
    for heading in (
        "Quiz",
        "Due date",
        "Duration",
        "Availability (UTC+7)",
        "Questions",
        "Action",
    ):
        assert f"<th>{heading}</th>" in html

    assert "/api/student/quizzes" in html
    assert 'quiz.end_at ? quiz.end_at.slice(0, 10) : "No due date"' in html
    assert "<noscript>" in html
    assert "Turn on JavaScript" in html
