import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db
import src.services.quiz_service as quiz_service

DUC_ID = 3
LAN_ID = 4
API_URL = "/api/student/quizzes"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
    with get_connection(path) as connection:
        connection.execute("UPDATE quiz SET start_at = NULL, end_at = NULL")
    return path


@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


def login(client, email="duc.student@example.edu"):
    response = client.post("/login", data={"email": email, "password": "MiniLMS2026!"})
    assert response.status_code == 302


def add_attempt(db_path, student_id, quiz_id, submitted):
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO attempt (student_id, quiz_id, started_at, submitted_at, score) "
            "VALUES (?, ?, '2026-10-18T08:00:00', ?, ?)",
            (
                student_id,
                quiz_id,
                "2026-10-18T08:10:00" if submitted else None,
                1.0 if submitted else None,
            ),
        )


def quizzes_by_id(client):
    response = client.get(API_URL)
    assert response.status_code == 200
    assert response.is_json
    return {quiz["quiz_id"]: quiz for quiz in response.get_json()["quizzes"]}


def test_api_lists_published_quizzes_from_the_database(client, db_path):
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET title = ? WHERE quiz_id = 1", ("Updated title from database",))
    login(client)

    quizzes = quizzes_by_id(client)

    assert sorted(quizzes) == list(range(1, 13))  # 13-14 draft, 15 closed
    assert quizzes[1] == {
        "quiz_id": 1,
        "title": "Updated title from database",
        "duration_minutes": 20,
        "duration_unlimited": False,
        "max_attempts": 1,
        "question_count": 1,
        "status": "not_started",
        "submitted_attempts": 0,
        "attempts_remaining": 1,
        "start_at": None,
        "end_at": None,
        "schedule_display": "No schedule",
        "start_at_display": "",
        "start_url": "/student/quiz/1/start",
    }


def test_question_count_counts_every_question(client, db_path):
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO question (quiz_id, content, points, position) VALUES (1, 'Extra?', 1, 2)"
        )
    login(client)

    assert quizzes_by_id(client)[1]["question_count"] == 2


def test_api_shows_the_students_status_for_each_quiz(client, db_path):
    add_attempt(db_path, DUC_ID, quiz_id=2, submitted=False)
    add_attempt(db_path, DUC_ID, quiz_id=3, submitted=True)
    add_attempt(db_path, LAN_ID, quiz_id=4, submitted=True)  # another student's attempt
    login(client)

    quizzes = quizzes_by_id(client)

    assert quizzes[1]["status"] == "not_started"
    assert quizzes[2]["status"] == "in_progress"
    assert quizzes[3]["status"] == "submitted"
    assert quizzes[4]["status"] == "not_started"


def test_api_marks_quizzes_outside_the_schedule_window(client, db_path, monkeypatch):
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET start_at = ?, end_at = ? WHERE quiz_id = 1",
            ("2026-10-20T04:00:00", "2026-10-20T05:00:00"),
        )
    monkeypatch.setattr(
        quiz_service,
        "utc_now_naive",
        lambda: quiz_service.parse_utc_timestamp("2026-10-20T03:00:00"),
    )
    login(client)

    quiz = quizzes_by_id(client)[1]

    assert quiz["status"] == "scheduled"
    assert quiz["schedule_display"] == (
        "20 Oct 2026, 11:00 (UTC+7) – 20 Oct 2026, 12:00 (UTC+7)"
    )


def test_api_formats_partial_schedule_and_unlimited_duration(client, db_path):
    with get_connection(db_path) as connection:
        connection.execute(
            """
            UPDATE quiz
            SET duration_unlimited = 1, start_at = ?, end_at = NULL
            WHERE quiz_id = 1
            """,
            ("2026-10-20T04:00:00",),
        )
    login(client)

    quiz = quizzes_by_id(client)[1]

    assert quiz["duration_unlimited"] is True
    assert quiz["schedule_display"] == "20 Oct 2026, 11:00 (UTC+7) – No deadline"


def test_started_quiz_shows_in_progress(client):
    login(client)
    client.post("/student/quiz/5/start")

    assert quizzes_by_id(client)[5]["status"] == "in_progress"


def test_api_returns_empty_list_when_nothing_is_published(client, db_path):
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET status = 'draft' WHERE status = 'published'")
    login(client)

    response = client.get(API_URL)

    assert response.status_code == 200
    assert response.get_json() == {"quizzes": []}


def test_api_redirects_guest_to_login(client):
    response = client.get(API_URL)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_api_rejects_lecturer(client):
    login(client, "ngan.lecturer@example.edu")

    assert client.get(API_URL).status_code == 403
