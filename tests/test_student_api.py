import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

DUC_ID = 3
LAN_ID = 4
API_URL = "/api/student/quizzes"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
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
        "end_at": "2026-10-10T23:59:00",
        "question_count": 1,
        "status": "not_started",
        "start_url": "/student/quiz/1/start",
    }


def test_api_lists_six_published_quizzes_and_excludes_unpublished_quizzes(client, db_path):
    with get_connection(db_path) as connection:
        connection.execute("UPDATE quiz SET status = 'draft' WHERE status = 'published'")
        connection.execute(
            "UPDATE quiz SET status = 'published', end_at = ? WHERE quiz_id BETWEEN 1 AND 5",
            ("2026-10-25T23:59:00",),
        )
        connection.execute(
            "UPDATE quiz SET status = 'published', end_at = NULL WHERE quiz_id = 6"
        )
    login(client)

    quizzes = quizzes_by_id(client)

    assert sorted(quizzes) == [1, 2, 3, 4, 5, 6]
    assert quizzes[1]["end_at"] == "2026-10-25T23:59:00"
    assert all(quizzes[quiz_id]["end_at"] == "2026-10-25T23:59:00" for quiz_id in range(1, 6))
    assert quizzes[6]["end_at"] is None


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
