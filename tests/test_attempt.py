from datetime import datetime, timedelta

import pytest
from markupsafe import escape

import src.services.attempt_service as attempt_service
from src.app import create_app
from src.db import get_connection
from src.errors import (
    ALREADY_SUBMITTED,
    NOT_YOUR_ATTEMPT,
    QUIZ_CLOSED,
    QUIZ_NOT_PUBLISHED,
    TIME_IS_UP,
)
from src.init_db import init_db

PUBLISHED_QUIZ = 1
DRAFT_QUIZ = 13
CLOSED_QUIZ = 15
DUC_ID = 3
LAN_ID = 4


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
    return path


@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


@pytest.fixture
def multi_question_client(db_path, client):
    """Quiz 1 with three questions; the extra two exist only in this test database."""
    with get_connection(db_path) as connection:
        for position in (2, 3):
            question_id = connection.execute(
                "INSERT INTO question (quiz_id, content, points, position) VALUES (?, ?, 1, ?)",
                (PUBLISHED_QUIZ, f"Extra question {position}?", position),
            ).lastrowid
            connection.executemany(
                "INSERT INTO choice (question_id, content, is_correct) VALUES (?, ?, ?)",
                [
                    (question_id, f"Q{position} option {index}", int(index == 1))
                    for index in range(1, 5)
                ],
            )
    return client


def login(client, email="duc.student@example.edu"):
    response = client.post("/login", data={"email": email, "password": "MiniLMS2026!"})
    assert response.status_code == 302


def shows_message(response, message):
    return str(escape(message)) in response.get_data(as_text=True)


def count_rows(db_path, sql, params=()):
    with get_connection(db_path) as connection:
        return connection.execute(sql, params).fetchone()[0]


def open_attempt_id(db_path, student_id=DUC_ID, quiz_id=PUBLISHED_QUIZ):
    with get_connection(db_path) as connection:
        return connection.execute(
            "SELECT attempt_id FROM attempt WHERE student_id = ? AND quiz_id = ? AND submitted_at IS NULL",
            (student_id, quiz_id),
        ).fetchone()[0]


def question_ids(db_path, quiz_id=PUBLISHED_QUIZ):
    with get_connection(db_path) as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT question_id FROM question WHERE quiz_id = ? ORDER BY position",
                (quiz_id,),
            )
        ]


def choice_ids(db_path, question_id):
    with get_connection(db_path) as connection:
        return [
            row[0]
            for row in connection.execute(
                "SELECT choice_id FROM choice WHERE question_id = ? ORDER BY choice_id",
                (question_id,),
            )
        ]


def answer(client, db_path, question_id, choice_id, go):
    return client.post(
        f"/student/quiz/{PUBLISHED_QUIZ}/take",
        data={
            "attempt_id": open_attempt_id(db_path),
            "question_id": question_id,
            "choice_id": choice_id,
            "go": go,
        },
    )


def checked_value(choice_id):
    return f'value="{choice_id}"\n                           checked'


def test_start_published_quiz_creates_attempt_and_shows_first_question(client, db_path):
    login(client)

    response = client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt WHERE student_id = ?", (DUC_ID,)) == 1

    page = client.get(response.headers["Location"])
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Introduction to Software Engineering" in html
    assert "Question 1 / 1" in html
    assert html.count('type="radio"') == 4
    assert 'data-remaining="1200"' in html


def test_closed_quiz_cannot_be_started(client, db_path):
    login(client)

    response = client.post(f"/student/quiz/{CLOSED_QUIZ}/start")

    assert response.status_code == 403
    assert shows_message(response, QUIZ_CLOSED)
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt") == 0


def test_draft_quiz_cannot_be_started(client, db_path):
    login(client)

    response = client.post(f"/student/quiz/{DRAFT_QUIZ}/start")

    assert response.status_code == 403
    assert shows_message(response, QUIZ_NOT_PUBLISHED)
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt") == 0


def test_already_submitted_quiz_cannot_be_started_again(client, db_path):
    with get_connection(db_path) as connection:
        connection.execute(
            "INSERT INTO attempt (student_id, quiz_id, started_at, submitted_at, score) "
            "VALUES (?, ?, '2026-10-01T08:00:00', '2026-10-01T08:10:00', 1)",
            (DUC_ID, PUBLISHED_QUIZ),
        )
    login(client)

    response = client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    assert response.status_code == 409
    assert shows_message(response, ALREADY_SUBMITTED)
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt") == 1


def test_starting_twice_resumes_the_same_attempt(client, db_path):
    login(client)

    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    first_id = open_attempt_id(db_path)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    assert open_attempt_id(db_path) == first_id
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt") == 1


def test_saved_answer_is_checked_when_question_is_reopened(client, db_path):
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    question_id = question_ids(db_path)[0]
    choice_id = choice_ids(db_path, question_id)[2]

    response = answer(client, db_path, question_id, choice_id, go=1)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("take?q=1")
    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert checked_value(choice_id) in html
    assert html.count("checked") == 1


def test_changing_an_answer_updates_the_same_row(client, db_path):
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    question_id = question_ids(db_path)[0]
    first, second = choice_ids(db_path, question_id)[:2]

    answer(client, db_path, question_id, first, go=1)
    answer(client, db_path, question_id, second, go=1)

    with get_connection(db_path) as connection:
        rows = connection.execute("SELECT choice_id FROM answer").fetchall()
    assert [row[0] for row in rows] == [second]


def test_navigating_without_choosing_saves_nothing(client, db_path):
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    response = client.post(
        f"/student/quiz/{PUBLISHED_QUIZ}/take",
        data={"attempt_id": open_attempt_id(db_path), "question_id": question_ids(db_path)[0], "go": 1},
    )

    assert response.status_code == 302
    assert count_rows(db_path, "SELECT COUNT(*) FROM answer") == 0


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", f"/student/quiz/{PUBLISHED_QUIZ}/start"),
        ("get", f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1"),
        ("post", f"/student/quiz/{PUBLISHED_QUIZ}/take"),
    ],
)
def test_unauthenticated_user_is_redirected_to_login(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", f"/student/quiz/{PUBLISHED_QUIZ}/start"),
        ("get", f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1"),
    ],
)
def test_lecturer_gets_403(client, db_path, method, path):
    login(client, "ngan.lecturer@example.edu")

    response = getattr(client, method)(path)

    assert response.status_code == 403
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt") == 0


def test_student_cannot_save_into_another_students_attempt(client, db_path):
    with get_connection(db_path) as connection:
        lan_attempt = connection.execute(
            "INSERT INTO attempt (student_id, quiz_id, started_at) VALUES (?, ?, ?)",
            (LAN_ID, PUBLISHED_QUIZ, attempt_service._now().strftime("%Y-%m-%dT%H:%M:%S")),
        ).lastrowid
    login(client)
    question_id = question_ids(db_path)[0]

    response = client.post(
        f"/student/quiz/{PUBLISHED_QUIZ}/take",
        data={
            "attempt_id": lan_attempt,
            "question_id": question_id,
            "choice_id": choice_ids(db_path, question_id)[0],
            "go": 1,
        },
    )

    assert response.status_code == 403
    assert shows_message(response, NOT_YOUR_ATTEMPT)
    assert count_rows(db_path, "SELECT COUNT(*) FROM answer") == 0


def test_take_page_without_starting_shows_404(client):
    login(client)

    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")

    assert response.status_code == 404
    assert "Take quiz" in response.get_data(as_text=True)


def test_answer_is_rejected_after_time_is_up(client, db_path, monkeypatch):
    start = datetime(2026, 10, 17, 8, 0, 0)
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    question_id = question_ids(db_path)[0]

    # Quiz 1 lasts 20 minutes.
    monkeypatch.setattr(attempt_service, "_now", lambda: start + timedelta(minutes=20))
    response = answer(client, db_path, question_id, choice_ids(db_path, question_id)[0], go=1)

    assert response.status_code == 403
    assert shows_message(response, TIME_IS_UP)
    assert count_rows(db_path, "SELECT COUNT(*) FROM answer") == 0


def test_remaining_seconds_counts_down_from_duration():
    start = "2026-10-17T08:00:00"

    assert attempt_service.remaining_seconds(start, 20, datetime(2026, 10, 17, 8, 0, 0)) == 1200
    assert attempt_service.remaining_seconds(start, 20, datetime(2026, 10, 17, 8, 5, 30)) == 870
    assert attempt_service.remaining_seconds(start, 20, datetime(2026, 10, 17, 9, 0, 0)) == 0


def test_next_and_previous_keep_the_saved_answer(multi_question_client, db_path):
    client = multi_question_client
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    first_question, second_question, _ = question_ids(db_path)
    chosen = choice_ids(db_path, first_question)[1]

    page = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1").get_data(as_text=True)
    assert "Question 1 / 3" in page
    assert page.count('name="go"') == 4  # Next + jump buttons 1..3

    response = answer(client, db_path, first_question, chosen, go=2)
    assert response.headers["Location"].endswith("take?q=2")
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Question 2 / 3" in page
    assert "Extra question 2?" in page
    assert "checked" not in page

    response = client.post(
        f"/student/quiz/{PUBLISHED_QUIZ}/take",
        data={"attempt_id": open_attempt_id(db_path), "question_id": second_question, "go": 1},
    )
    assert response.headers["Location"].endswith("take?q=1")
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Question 1 / 3" in page
    assert checked_value(chosen) in page


def test_number_button_jumps_straight_to_question(multi_question_client, db_path):
    client = multi_question_client
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    response = client.post(
        f"/student/quiz/{PUBLISHED_QUIZ}/take",
        data={"attempt_id": open_attempt_id(db_path), "question_id": question_ids(db_path)[0], "go": 3},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("take?q=3")
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Question 3 / 3" in page
    assert "Extra question 3?" in page
    assert "Next question" not in page


def test_question_number_out_of_range_shows_404(multi_question_client, db_path):
    client = multi_question_client
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    assert client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=4").status_code == 404
