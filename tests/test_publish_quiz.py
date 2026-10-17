"""Tests for US04: Lecturer publishes and closes a quiz (BR2, BR3, BR4)."""

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db


def _login_as(client, email, password="MiniLMS2026!"):
    """Helper to log in via the login route."""
    client.post("/logout")
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def test_lecturer_can_view_publish_page(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
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
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()

    _login_as(client, "ngan.lecturer@example.edu", "MiniLMS2026!")

    # Quiz 1 is already published
    response = client.post("/lecturer/quiz/1/publish")
    assert response.status_code == 409


def test_close_quiz_updates_status_and_blocks_new_student_attempts(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)
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
