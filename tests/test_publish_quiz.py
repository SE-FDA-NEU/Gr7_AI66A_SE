from __future__ import annotations
"""Tests for US04: Lecturer publishes and closes a quiz (BR2, BR3, BR4)."""

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db
import src.services.quiz_service as quiz_service


def _login_as(client, email, password="MiniLMS2026!"):
    """Helper to log in via the login route."""
    client.post("/logout")
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def test_lecturer_can_view_publish_page(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET end_at = NULL WHERE quiz_id = 1")
        connection.commit()
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    # User 1: Ngan (lecturer) owns quiz 13 (draft)
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")
    response = client.get("/lecturer/quiz/13/publish")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Advanced Analytics" in html
    assert "Draft" in html or "draft" in html
    assert "Publish bài Quiz" in html or "Publish" in html
    assert 'name="start_at"' in html
    assert 'name="end_at"' in html
    assert 'name="duration"' in html
    assert 'name="duration_unlimited"' in html


def test_lecturer_can_save_quiz_schedule_in_hanoi_time(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET end_at = NULL WHERE quiz_id = 1")
        connection.commit()
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    response = client.post(
        "/lecturer/quiz/13/schedule",
        data={"start_at": "2026-10-20T11:00", "end_at": "2026-10-20T12:00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Quiz schedule saved successfully." in response.get_data(as_text=True)
    with get_connection(db_path) as connection:
        schedule = connection.execute(
            "SELECT start_at, end_at FROM quiz WHERE quiz_id = 13"
        ).fetchone()
    assert tuple(schedule) == ("2026-10-20T04:00:00", "2026-10-20T05:00:00")


def test_lecturer_can_set_a_deadline_without_a_start_time(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    response = client.post(
        "/lecturer/quiz/13/schedule",
        data={"start_at": "", "end_at": "2026-10-20T12:00"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with get_connection(db_path) as connection:
        schedule = connection.execute(
            "SELECT start_at, end_at FROM quiz WHERE quiz_id = 13"
        ).fetchone()
    assert tuple(schedule) == (None, "2026-10-20T05:00:00")


def test_lecturer_can_update_quiz_time_limit_from_schedule(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    response = client.post(
        "/lecturer/quiz/13/schedule",
        data={
            "start_at": "2026-10-20T11:00",
            "end_at": "",
            "duration": "45",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    with get_connection(db_path) as connection:
        settings = connection.execute(
            "SELECT start_at, end_at, duration_minutes, duration_unlimited "
            "FROM quiz WHERE quiz_id = 13"
        ).fetchone()
    assert tuple(settings) == ("2026-10-20T04:00:00", None, 45, 0)

    unlimited = client.post(
        "/lecturer/quiz/13/schedule",
        data={
            "start_at": "2026-10-20T11:00",
            "end_at": "",
            "duration_unlimited": "yes",
        },
        follow_redirects=True,
    )
    assert unlimited.status_code == 200
    with get_connection(db_path) as connection:
        duration = connection.execute(
            "SELECT duration_unlimited FROM quiz WHERE quiz_id = 13"
        ).fetchone()[0]
    assert duration == 1


def test_deadline_expiry_closes_quiz_and_republish_requires_new_deadline(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    now = quiz_service.parse_utc_timestamp("2026-10-24T06:00:00")
    monkeypatch.setattr(quiz_service, "utc_now_naive", lambda: now)
    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE quiz
            SET start_at = NULL, end_at = '2026-10-20T05:00:00'
            WHERE quiz_id = 1
            """
        )
        connection.commit()

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    manage = client.get("/lecturer/quiz/1/publish")
    html = manage.get_data(as_text=True)
    assert manage.status_code == 200
    assert "Close Quiz" not in html
    assert "Publish Quiz Again" in html
    assert "disabled aria-describedby=\"publish-block-reason\"" in html
    with get_connection(db_path) as connection:
        quiz = connection.execute(
            "SELECT status, closed_by_deadline FROM quiz WHERE quiz_id = 1"
        ).fetchone()
    assert tuple(quiz) == ("closed", 1)

    rejected = client.post("/lecturer/quiz/1/publish")
    assert rejected.status_code == 422
    assert "Change the quiz deadline before publishing it again." in rejected.get_data(as_text=True)

    schedule = client.post(
        "/lecturer/quiz/1/schedule",
        data={
            "start_at": "",
            "end_at": "2026-10-30T12:00",
            "duration": "20",
            "max_attempts": "1",
        },
        follow_redirects=True,
    )
    assert schedule.status_code == 200
    assert "disabled aria-describedby=\"publish-block-reason\"" not in schedule.get_data(as_text=True)

    republished = client.post("/lecturer/quiz/1/publish", follow_redirects=True)
    assert republished.status_code == 200
    with get_connection(db_path) as connection:
        quiz = connection.execute(
            "SELECT status, closed_by_deadline, last_published_end_at "
            "FROM quiz WHERE quiz_id = 1"
        ).fetchone()
    assert tuple(quiz) == ("published", 0, "2026-10-30T05:00:00")


def test_max_attempts_must_be_a_positive_integer(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    response = client.post(
        "/lecturer/quiz/13/schedule",
        data={"start_at": "", "end_at": "", "max_attempts": "0"},
    )

    assert response.status_code == 422
    assert "Maximum attempts must be a positive whole number." in response.get_data(as_text=True)
    with get_connection(db_path) as connection:
        value = connection.execute(
            "SELECT max_attempts FROM quiz WHERE quiz_id = 13"
        ).fetchone()[0]
    assert value == 1


def test_invalid_schedule_is_rejected_and_other_lecturers_cannot_change_it(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")
    invalid = client.post(
        "/lecturer/quiz/13/schedule",
        data={"start_at": "2026-10-20T12:00", "end_at": "2026-10-20T11:00"},
    )
    assert invalid.status_code == 422
    assert "end time must be later" in invalid.get_data(as_text=True)

    _login_as(client, "nam.lecturer@example.edu", "MiniLMS2026!")
    forbidden = client.post(
        "/lecturer/quiz/13/schedule",
        data={"start_at": "", "end_at": ""},
    )
    assert forbidden.status_code == 403


def test_publish_valid_quiz_updates_status_to_published(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    # Quiz 13 is draft and has 1 valid question with 4 choices (1 correct)
    response = client.post("/lecturer/quiz/13/publish", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Published" in html or "published" in html
    assert "Đóng bài Quiz" in html or "Close Quiz" in html

    # Verify directly in SQLite
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM quiz WHERE quiz_id = 13").fetchone()
        assert row["status"] == "published"


def test_publish_quiz_rejected_when_not_quiz_owner_br2(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    # User 2: Nam (lecturer) tries to access quiz 13 (owned by User 1: Ngan)
    _login_as(client, "nam.lecturer@example.edu", "MiniLMS2026!")

    # GET publish page of another lecturer
    response = client.get("/lecturer/quiz/13/publish")
    assert response.status_code == 403
    html = response.get_data(as_text=True)
    assert "Bạn không có quyền sửa quiz này vì nó thuộc giảng viên khác" in html or "You do not have permission to edit this quiz" in html

    # POST publish quiz of another lecturer
    response_post = client.post("/lecturer/quiz/13/publish")
    assert response_post.status_code == 403


def test_publish_quiz_rejected_when_no_questions_br3(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)

    # Insert a draft quiz with 0 questions owned by lecturer 1
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO quiz (lecturer_id, title, status, duration_minutes) VALUES (?, ?, ?, ?)",
            (1, "Empty Quiz No Questions", "draft", 20),
        )
        empty_quiz_id = cursor.lastrowid
        conn.commit()

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    # Attempt to publish empty quiz
    response = client.post(f"/lecturer/quiz/{empty_quiz_id}/publish")
    assert response.status_code == 422
    html = response.get_data(as_text=True)
    assert "Chưa thể publish: bài quiz phải có ít nhất 1 câu hỏi" in html or "A quiz must contain at least 1 question" in html

    # Verify quiz status is still draft
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM quiz WHERE quiz_id = ?", (empty_quiz_id,)).fetchone()
        assert row["status"] == "draft"


def test_publish_quiz_rejected_when_missing_correct_choice_br3(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)

    # Insert a draft quiz with a question where none of the choices is correct
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO quiz (lecturer_id, title, status, duration_minutes) VALUES (?, ?, ?, ?)",
            (1, "Quiz With Invalid Question", "draft", 30),
        )
        invalid_quiz_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO question (quiz_id, content, points, position) VALUES (?, ?, ?, ?)",
            (invalid_quiz_id, "Question without correct choice", 1, 1),
        )
        q_id = cursor.lastrowid

        # 4 choices, none is correct
        for i in range(1, 5):
            cursor.execute(
                "INSERT INTO choice (question_id, content, is_correct) VALUES (?, ?, ?)",
                (q_id, f"Option {i}", 0),
            )
        conn.commit()

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    response = client.post(f"/lecturer/quiz/{invalid_quiz_id}/publish")
    assert response.status_code == 422
    html = response.get_data(as_text=True)
    assert "câu 1 chưa có đáp án đúng" in html or "Please select one correct option" in html


def test_publish_already_published_quiz_returns_409(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET start_at = NULL, end_at = NULL WHERE quiz_id = 1"
        )
        connection.commit()
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    # Quiz 1 is already published
    response = client.post("/lecturer/quiz/1/publish")
    assert response.status_code == 409


def test_close_quiz_updates_status_and_blocks_new_student_attempts(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET start_at = NULL, end_at = NULL WHERE quiz_id = 1"
        )
        connection.commit()
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    # Lecturer 1 closes Quiz 1
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")
    response_close = client.post("/lecturer/quiz/1/close", follow_redirects=True)
    assert response_close.status_code == 200

    with get_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM quiz WHERE quiz_id = 1").fetchone()
        assert row["status"] == "closed"

    # Now log in as Student Duc and attempt to start Quiz 1
    _login_as(client, "duc.student@example.edu", "MiniLMS2026!")
    response_start = client.post("/student/quiz/1/start")
    assert response_start.status_code == 403
    html = response_start.get_data(as_text=True)
    assert "This quiz is closed" in html or "closed" in html


def test_student_cannot_access_publish_page_br1(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    # Student logs in
    _login_as(client, "duc.student@example.edu", "MiniLMS2026!")
    response = client.get("/lecturer/quiz/1/publish")
    assert response.status_code == 403


def test_lecturer_can_republish_closed_quiz(tmp_path):
    """A valid closed quiz can be reopened by its owner."""
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute("UPDATE quiz SET start_at = NULL, end_at = NULL WHERE quiz_id = 1")
        cursor = conn.execute(
            """
            INSERT INTO attempt (student_id, quiz_id, started_at, submitted_at, score)
            VALUES (?, ?, '2026-10-18T09:00:00', '2026-10-18T09:15:00', ?)
            """,
            (3, 1, 9.5),
        )
        submitted_attempt_id = cursor.lastrowid
        conn.commit()

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    # Close quiz 1 first
    close_res = client.post("/lecturer/quiz/1/close", follow_redirects=True)
    assert close_res.status_code == 200

    publish_page = client.get("/lecturer/quiz/1/publish")
    assert publish_page.status_code == 200
    assert "Publish Quiz Again" in publish_page.get_data(as_text=True)

    response = client.post("/lecturer/quiz/1/publish", follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Published" in html
    assert "Quiz published successfully." in html
    assert "Close Quiz" in html

    with get_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM quiz WHERE quiz_id = 1").fetchone()
        assert row["status"] == "published"
        attempt = conn.execute(
            "SELECT submitted_at, score FROM attempt WHERE attempt_id = ?",
            (submitted_attempt_id,),
        ).fetchone()
        assert attempt["submitted_at"] == "2026-10-18T09:15:00"
        assert attempt["score"] == 9.5

    _login_as(client, "lan.student@example.edu", "MiniLMS2026!")
    start_response = client.post("/student/quiz/1/start")
    assert start_response.status_code == 302
    assert start_response.headers["Location"].endswith("/take?q=1")


def test_cannot_close_draft_quiz_must_be_published_first(tmp_path):
    """Test state machine: Draft -> Closed is forbidden (must be published first)."""
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    # Quiz 13 is Draft
    response = client.post("/lecturer/quiz/13/close")
    assert response.status_code == 400
    html = response.get_data(as_text=True)
    assert "phải được publish trước khi đóng" in html or "must be published before it can be closed" in html

    with get_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM quiz WHERE quiz_id = 13").fetchone()
        assert row["status"] == "draft"


def test_cannot_close_already_closed_quiz(tmp_path):
    """Test state machine: Closed -> Closed returns 409 conflict."""
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    # Close quiz 1
    client.post("/lecturer/quiz/1/close")

    # Try to close it again
    response = client.post("/lecturer/quiz/1/close")
    assert response.status_code == 409
    html = response.get_data(as_text=True)
    assert "Bài quiz này đã được đóng trước đó" in html or "already closed" in html


def test_closed_quiz_behavior_preserves_submitted_attempts_and_blocks_new_ones(tmp_path):
    """
    Test that closing a quiz:
    1. Blocks new student attempts (BR4).
    2. Completely preserves previously submitted attempts and scores.
    """
    db_path = tmp_path / "minilms.db"
    init_db(db_path)

    # Student 3 (Duc) has submitted an attempt on Quiz 1
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE quiz SET start_at = NULL, end_at = NULL WHERE quiz_id = 1"
        )
        cursor.execute(
            """
            INSERT INTO attempt (student_id, quiz_id, started_at, submitted_at, score)
            VALUES (?, ?, '2026-10-18T09:00:00', '2026-10-18T09:15:00', 9.5)
            """,
            (3, 1),
        )
        attempt_id = cursor.lastrowid
        conn.commit()

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    # Lecturer closes Quiz 1
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")
    res_close = client.post("/lecturer/quiz/1/close")
    assert res_close.status_code in (200, 302)

    # Verify Quiz 1 status is closed
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM quiz WHERE quiz_id = 1").fetchone()
        assert row["status"] == "closed"

    # Verify previously submitted attempt is untouched
    with get_connection(db_path) as conn:
        attempt_row = conn.execute(
            "SELECT attempt_id, student_id, score, submitted_at FROM attempt WHERE attempt_id = ?",
            (attempt_id,),
        ).fetchone()
        assert attempt_row is not None
        assert attempt_row["score"] == 9.5
        assert attempt_row["submitted_at"] == "2026-10-18T09:15:00"

    # Another student (User 4: Lan) tries to start the closed quiz -> blocked with 403
    _login_as(client, "lan.student@example.edu", "MiniLMS2026!")
    res_start = client.post("/student/quiz/1/start")
    assert res_start.status_code == 403
    html = res_start.get_data(as_text=True)
    assert "This quiz is closed" in html or "closed" in html


def test_friendly_ui_error_messages_rendered_on_br3_and_br2(tmp_path):
    """Verify BR2 and BR3 display human-readable error messages on the UI, not just raw HTTP codes."""
    db_path = tmp_path / "minilms.db"
    init_db(db_path)

    # Insert a draft quiz with 0 questions
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO quiz (lecturer_id, title, status, duration_minutes) VALUES (?, ?, ?, ?)",
            (1, "Empty Demo Quiz", "draft", 25),
        )
        empty_id = cursor.lastrowid
        conn.commit()

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    # Test BR3: Friendly error message in alert banner on page
    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")
    post_res = client.post(f"/lecturer/quiz/{empty_id}/publish")
    assert post_res.status_code == 422
    html_br3 = post_res.get_data(as_text=True)
    assert "Chưa thể publish: bài quiz phải có ít nhất 1 câu hỏi" in html_br3
    assert 'role="alert"' in html_br3

    # Test BR2: Non-owner gets friendly UI with navigation button
    _login_as(client, "nam.lecturer@example.edu", "MiniLMS2026!")
    get_res = client.get(f"/lecturer/quiz/{empty_id}/publish")
    assert get_res.status_code == 403
    html_br2 = get_res.get_data(as_text=True)
    assert "Bạn không có quyền sửa quiz này vì nó thuộc giảng viên khác" in html_br2
    assert "Dashboard Giảng viên" in html_br2
