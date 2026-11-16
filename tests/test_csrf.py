"""CSRF protection: every state-changing request needs the session's token."""
from __future__ import annotations

import re
from html.parser import HTMLParser

import pytest

from src.app import create_app
from src.db import get_connection
from src.errors import CSRF_FAILED
from src.init_db import init_db

PASSWORD = "MiniLMS2026!"
LECTURER = "ngan.lecturer@example.edu"
STUDENT = "duc.student@example.edu"
TOKEN_RE = re.compile(r'name="csrf_token" value="([^"]+)"')


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms_test.db"
    init_db(path)
    with get_connection(path) as connection:
        connection.execute("UPDATE quiz SET start_at = NULL, end_at = NULL")
    return path


@pytest.fixture
def app(db_path):
    return create_app(
        {"TESTING": True, "DATABASE_PATH": str(db_path), "WTF_CSRF_ENABLED": True}
    )


@pytest.fixture
def client(app):
    return app.test_client()


def token_from(client, url):
    """Read the token a page embeds in its form (what a browser would send)."""
    page = client.get(url).get_data(as_text=True)
    match = TOKEN_RE.search(page)
    assert match, f"{url} has no csrf_token field"
    return match.group(1)


def login(client, email, password=PASSWORD):
    token = token_from(client, "/login")
    return client.post(
        "/login", data={"email": email, "password": password, "csrf_token": token}
    )


class FormCollector(HTMLParser):
    """Collect every POST form on a page and whether it holds a csrf_token field."""

    def __init__(self):
        super().__init__()
        self.forms = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.forms.append(
                {
                    "action": attrs.get("action"),
                    "method": (attrs.get("method") or "get").lower(),
                    "has_token": False,
                }
            )
        elif tag == "input" and self.forms and attrs.get("name") == "csrf_token":
            self.forms[-1]["has_token"] = True


def post_forms(client, url):
    collector = FormCollector()
    response = client.get(url)
    assert response.status_code == 200, url
    collector.feed(response.get_data(as_text=True))
    return [form for form in collector.forms if form["method"] == "post"]


def quiz_count(db_path):
    with get_connection(db_path) as connection:
        return connection.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]


def test_csrf_is_enabled_by_default_outside_tests(tmp_path):
    app = create_app(
        {"TESTING": False, "SECRET_KEY": "k", "DATABASE_PATH": str(tmp_path / "x.db")}
    )

    assert app.config["WTF_CSRF_ENABLED"] is True
    # A long quiz or editing session must not outlive its token.
    assert app.config["WTF_CSRF_TIME_LIMIT"] is None


def test_login_without_token_is_rejected(client):
    response = client.post("/login", data={"email": STUDENT, "password": PASSWORD})

    assert response.status_code == 400
    assert CSRF_FAILED in response.get_data(as_text=True)
    with client.session_transaction() as user_session:
        assert "user_id" not in user_session


def test_login_with_a_wrong_token_is_rejected_without_leaking_the_reason(client):
    client.get("/login")

    response = client.post(
        "/login",
        data={"email": STUDENT, "password": PASSWORD, "csrf_token": "forged"},
    )

    assert response.status_code == 400
    page = response.get_data(as_text=True)
    assert CSRF_FAILED in page
    assert "session token" not in page.lower()


def test_login_with_a_valid_token_works(client):
    response = login(client, STUDENT)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/dashboard")


def test_lecturer_post_without_token_changes_nothing(client, db_path):
    login(client, LECTURER)
    before = quiz_count(db_path)

    response = client.post("/quiz/create", data={"title": "forged", "duration": "10"})

    assert response.status_code == 400
    assert quiz_count(db_path) == before


def test_lecturer_post_with_token_succeeds(client, db_path):
    login(client, LECTURER)
    before = quiz_count(db_path)
    token = token_from(client, "/quiz/create")

    response = client.post(
        "/quiz/create",
        data={"title": "real", "duration": "10", "csrf_token": token},
    )

    assert response.status_code == 302
    assert quiz_count(db_path) == before + 1


def test_token_from_before_login_is_useless_after_login(client, db_path):
    stale = token_from(client, "/login")
    client.post(
        "/login", data={"email": LECTURER, "password": PASSWORD, "csrf_token": stale}
    )
    before = quiz_count(db_path)

    response = client.post(
        "/quiz/create",
        data={"title": "x", "duration": "10", "csrf_token": stale},
    )

    assert response.status_code == 400
    assert quiz_count(db_path) == before


def test_logout_requires_a_token(client):
    login(client, STUDENT)

    assert client.post("/logout").status_code == 400
    with client.session_transaction() as user_session:
        assert "user_id" in user_session  # still signed in


def test_json_requests_may_send_the_token_in_a_header(client, db_path):
    login(client, LECTURER)
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET status = 'draft' WHERE quiz_id = 1")
    token = token_from(client, "/lecturer/dashboard")

    without = client.post("/lecturer/quiz/1/publish", json={})
    with_header = client.post(
        "/lecturer/quiz/1/publish", json={}, headers={"X-CSRFToken": token}
    )

    assert without.status_code == 400
    assert with_header.status_code == 200


def test_every_post_form_on_every_page_carries_the_token(client, db_path):
    forms = []
    forms += post_forms(client, "/login")

    login(client, LECTURER)
    forms += post_forms(client, "/lecturer/dashboard")
    forms += post_forms(client, "/quiz/create")
    # Draft state shows publish, schedule, add-question and edit-question forms ...
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET status = 'draft' WHERE quiz_id = 1")
    draft_forms = post_forms(client, "/lecturer/quiz/1/publish")
    # ... published state shows the close form.
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET status = 'published' WHERE quiz_id = 1")
    published_forms = post_forms(client, "/lecturer/quiz/1/publish")
    forms += draft_forms + published_forms

    client.post("/logout", data={"csrf_token": token_from(client, "/lecturer/dashboard")})
    login(client, STUDENT)
    forms += post_forms(client, "/student/dashboard")
    token = token_from(client, "/student/dashboard")
    client.post("/student/quiz/1/start", data={"csrf_token": token})
    forms += post_forms(client, "/student/quiz/1/take?q=1")
    forms += post_forms(client, "/student/quiz/1/review")

    actions = {form["action"] for form in forms}
    # The crawl really reached each kind of form ...
    assert any(a.endswith("/login") for a in actions)
    assert any(a.endswith("/logout") for a in actions)
    assert any(a.endswith("/quiz/create") for a in actions)
    assert any(a.endswith("/questions") for a in actions)
    assert any("/edit" in a for a in actions)
    assert any(a.endswith("/schedule") for a in actions)
    assert any(a.endswith("/publish") for a in actions)
    assert any(a.endswith("/close") for a in actions)
    assert any(a.endswith("/take") for a in actions)
    assert any(a.endswith("/submit") for a in actions)
    # ... and none of them is missing its token.
    missing = [form["action"] for form in forms if not form["has_token"]]
    assert missing == []


def test_student_can_take_and_submit_a_quiz_with_tokens(client, db_path):
    login(client, STUDENT)

    token = token_from(client, "/student/dashboard")
    assert client.post(
        "/student/quiz/1/start", data={"csrf_token": token}
    ).status_code == 302

    with get_connection(db_path) as connection:
        question_id = connection.execute(
            "SELECT question_id FROM question WHERE quiz_id = 1 ORDER BY position LIMIT 1"
        ).fetchone()[0]
        choice_id = connection.execute(
            "SELECT choice_id FROM choice WHERE question_id = ? LIMIT 1", (question_id,)
        ).fetchone()[0]
        attempt_id = connection.execute(
            "SELECT attempt_id FROM attempt WHERE student_id = 3 AND quiz_id = 1"
        ).fetchone()[0]

    token = token_from(client, "/student/quiz/1/take?q=1")
    saved = client.post(
        "/student/quiz/1/take",
        data={
            "attempt_id": attempt_id,
            "question_id": question_id,
            "choice_id": choice_id,
            "go": "review",
            "csrf_token": token,
        },
    )
    assert saved.status_code == 302

    token = token_from(client, "/student/quiz/1/review")
    submitted = client.post(
        "/student/quiz/1/submit",
        data={"attempt_id": attempt_id, "confirm": "yes", "csrf_token": token},
    )
    assert submitted.status_code == 302
    assert submitted.headers["Location"].endswith("/student/quiz/1/submitted")


def test_student_post_without_token_does_not_start_an_attempt(client, db_path):
    login(client, STUDENT)

    response = client.post("/student/quiz/1/start")

    assert response.status_code == 400
    with get_connection(db_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM attempt").fetchone()[0] == 0


def test_forms_built_by_javascript_include_the_token(client):
    """The Take quiz forms are created in the browser, so the crawl cannot see them."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "src"
    builders = [
        path
        for path in [*root.glob("templates/*.html"), *root.glob("static/js/*.js")]
        if 'createElement("form")' in path.read_text(encoding="utf-8")
        or "createElement('form')" in path.read_text(encoding="utf-8")
    ]

    assert builders, "expected the student dashboard to build forms in JavaScript"
    for path in builders:
        assert "csrf_token" in path.read_text(encoding="utf-8"), (
            f"{path.name} builds a form in JavaScript without a csrf_token field"
        )


def test_student_dashboard_script_embeds_the_session_token(client):
    login(client, STUDENT)

    page = client.get("/student/dashboard").get_data(as_text=True)
    token = TOKEN_RE.search(page).group(1)

    assert f'CSRF_TOKEN = "{token}"' in page


def test_a_request_rejected_for_csrf_is_still_logged_with_its_duration(client, capsys):
    import json

    client.post("/login", data={"email": STUDENT, "password": PASSWORD})

    records = [
        json.loads(line)
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("{")
    ]
    rejected = [r for r in records if r["method"] == "POST" and r["path"] == "/login"]
    assert [r["status_code"] for r in rejected] == [400]
    assert isinstance(rejected[0]["duration_ms"], float)
