"""Tests for the lecturer's quiz dashboard (US14)."""

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db


def _dashboard_client(tmp_path, email="ngan.lecturer@example.edu"):
    db_path = tmp_path / "dashboard.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    login = client.post(
        "/login",
        data={"email": email, "password": "MiniLMS2026!"},
    )
    assert login.status_code == 302
    return client, db_path


def _insert_quiz(db_path, lecturer_id, title, status="draft"):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO quiz (lecturer_id, title, status, duration_minutes)
            VALUES (?, ?, ?, ?)
            """,
            (lecturer_id, title, status, 30),
        )
        conn.commit()
        return cursor.lastrowid


def test_dashboard_lists_only_current_lecturers_quizzes(tmp_path):
    client, db_path = _dashboard_client(tmp_path)
    owned_title = "Lecturer One Owned Quiz"
    other_title = "Lecturer Two Owned Quiz"
    _insert_quiz(db_path, 1, owned_title)
    _insert_quiz(db_path, 2, other_title)

    response = client.get("/lecturer/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert owned_title in html
    assert other_title not in html


def test_guest_is_redirected_to_login(tmp_path):
    db_path = tmp_path / "guest-dashboard.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})

    response = app.test_client().get("/lecturer/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_dashboard_requires_lecturer_role(tmp_path):
    client, _ = _dashboard_client(tmp_path, "duc.student@example.edu")

    response = client.get("/lecturer/dashboard")

    assert response.status_code == 403


def test_lecturer_can_log_out_from_dashboard(tmp_path):
    client, _ = _dashboard_client(tmp_path)

    dashboard = client.get("/lecturer/dashboard")
    html = dashboard.get_data(as_text=True)

    assert dashboard.status_code == 200
    assert 'class="logout-form" method="post" action="/logout"' in html
    assert 'data-confirm="Are you sure you want to sign out?"' in html

    response = client.post("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert client.get("/lecturer/dashboard").headers["Location"].endswith("/login")


def test_dashboard_shows_attempt_counts_from_database(tmp_path):
    client, db_path = _dashboard_client(tmp_path)
    quiz_id = _insert_quiz(db_path, 1, "Attempt Count Target")
    unrelated_quiz_id = _insert_quiz(db_path, 1, "Unrelated Quiz")
    with get_connection(db_path) as conn:
        attempt_count = 2
        conn.executemany(
            """
            INSERT INTO attempt (student_id, quiz_id, started_at, submitted_at)
            VALUES (?, ?, '2026-10-18T09:00:00', '2026-10-18T09:10:00')
            """,
            [(3, quiz_id), (4, quiz_id), (5, unrelated_quiz_id)],
        )
        conn.commit()

    response = client.get("/lecturer/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    rows = html.split("<tr>")[1:]
    quiz_rows = {
        row.split("</tr>", 1)[0]
        for row in rows
        if "Attempt Count Target" in row or "Unrelated Quiz" in row
    }
    assert len(quiz_rows) == 2
    target_row = next(row for row in quiz_rows if "Attempt Count Target" in row)
    unrelated_row = next(row for row in quiz_rows if "Unrelated Quiz" in row)
    assert f"{attempt_count} attempts" in target_row
    assert "1 attempts" in unrelated_row
    assert f'href="/lecturer/quiz/{quiz_id}/attempts"' in target_row


def test_lecturer_can_view_attempt_list_and_answer_review(tmp_path):
    client, db_path = _dashboard_client(tmp_path)
    with get_connection(db_path) as conn:
        question = conn.execute(
            "SELECT question_id, content FROM question WHERE quiz_id = 1"
        ).fetchone()
        choices = conn.execute(
            "SELECT choice_id, content, is_correct FROM choice WHERE question_id = ? ORDER BY choice_id",
            (question["question_id"],),
        ).fetchall()
        correct_choice = next(choice for choice in choices if choice["is_correct"])
        wrong_choice = next(choice for choice in choices if not choice["is_correct"])

        submitted_attempt_id = conn.execute(
            """
            INSERT INTO attempt (
                student_id, quiz_id, started_at, submitted_at, score
            ) VALUES (3, 1, '2026-10-20T09:00:00', '2026-10-20T09:10:00', 0.0)
            """
        ).lastrowid
        conn.execute(
            "INSERT INTO answer (attempt_id, question_id, choice_id) VALUES (?, ?, ?)",
            (submitted_attempt_id, question["question_id"], wrong_choice["choice_id"]),
        )

        open_attempt_id = conn.execute(
            """
            INSERT INTO attempt (student_id, quiz_id, started_at)
            VALUES (4, 1, '2026-10-20T09:30:00')
            """
        ).lastrowid
        conn.execute(
            "INSERT INTO answer (attempt_id, question_id, choice_id) VALUES (?, ?, ?)",
            (open_attempt_id, question["question_id"], correct_choice["choice_id"]),
        )
        conn.commit()

    attempts_response = client.get("/lecturer/quiz/1/attempts")
    attempts_html = attempts_response.get_data(as_text=True)
    assert attempts_response.status_code == 200
    assert "duc.student@example.edu" in attempts_html
    assert "lan.student@example.edu" in attempts_html
    assert "In progress" in attempts_html
    assert f'href="/lecturer/quiz/1/attempts/{submitted_attempt_id}"' in attempts_html

    detail_response = client.get(
        f"/lecturer/quiz/1/attempts/{submitted_attempt_id}"
    )
    detail_html = detail_response.get_data(as_text=True)
    assert detail_response.status_code == 200
    assert question["content"] in detail_html
    assert wrong_choice["content"] in detail_html
    assert correct_choice["content"] in detail_html
    assert "Incorrect" in detail_html


def test_lecturer_attempt_pages_enforce_quiz_ownership_and_attempt_scope(tmp_path):
    client, _ = _dashboard_client(tmp_path, "nam.lecturer@example.edu")

    forbidden = client.get("/lecturer/quiz/1/attempts")
    assert forbidden.status_code == 403

    not_found = client.get("/lecturer/quiz/14/attempts/1")
    assert not_found.status_code == 404

def test_dashboard_shows_empty_state_and_create_link(tmp_path):
    client, db_path = _dashboard_client(tmp_path)

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO user (email, password_hash, role, name)
            VALUES (?, ?, ?, ?)
            """,
            (
                "empty.lecturer@example.edu",
                "unused",
                "lecturer",
                "Empty Lecturer",
            ),
        )
        lecturer_id = cursor.lastrowid
        conn.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = lecturer_id
        sess["role"] = "lecturer"

    response = client.get("/lecturer/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "You have no quizzes yet" in html
    assert 'href="/quiz/create"' in html


def test_dashboard_navigation_links_to_create_edit_and_publish(tmp_path):
    client, db_path = _dashboard_client(tmp_path)
    draft_quiz_id = _insert_quiz(db_path, 1, "Navigation Draft Quiz")
    published_quiz_id = _insert_quiz(
        db_path, 1, "Navigation Published Quiz", status="published"
    )
    closed_quiz_id = _insert_quiz(
        db_path, 1, "Navigation Closed Quiz", status="closed"
    )

    response = client.get("/lecturer/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '<nav aria-label="Lecturer navigation">' not in html
    assert '<h1>My Quizzes</h1>' in html
    assert 'href="/quiz/create"' in html
    assert html.count(f'href="/lecturer/quiz/{draft_quiz_id}/publish"') == 1
    assert html.count(f'href="/lecturer/quiz/{published_quiz_id}/publish"') == 1
    assert html.count(f'href="/lecturer/quiz/{closed_quiz_id}/publish"') == 1
    assert ">Manage</a>" not in html

    create_page = client.get("/quiz/create")
    edit_questions = client.get(f"/lecturer/quiz/{draft_quiz_id}/publish")
    publish_page = client.get(f"/lecturer/quiz/{draft_quiz_id}/publish")
    closed_publish_page = client.get(f"/lecturer/quiz/{closed_quiz_id}/publish")
    assert create_page.status_code == 200
    assert edit_questions.status_code == 200
    assert publish_page.status_code == 200
    assert closed_publish_page.status_code == 200


def test_dashboard_displays_human_readable_quiz_statuses(tmp_path):
    client, db_path = _dashboard_client(tmp_path)
    _insert_quiz(db_path, 1, "Dashboard Draft", status="draft")
    _insert_quiz(db_path, 1, "Dashboard Published", status="published")
    _insert_quiz(db_path, 1, "Dashboard Closed", status="closed")

    response = client.get("/lecturer/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Closed" in html
    assert "Draft" in html
    assert "Published" in html
