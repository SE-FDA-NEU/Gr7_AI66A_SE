
import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db
from src.errors import (
    CHOICES_REQUIRED,
    INVALID_POINTS,
    NOT_QUIZ_OWNER,
    SELECT_CORRECT_OPTION,
)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
    return path


@pytest.fixture
def client(db_path):
    app = create_app({
        "TESTING": True,
        "DATABASE_PATH": db_path,
    })
    return app.test_client()


def login(client, email="ngan.lecturer@example.edu"):
    response = client.post(
        "/login",
        data={
            "email": email,
            "password": "MiniLMS2026!",
        },
    )
    assert response.status_code == 302


def question_count(db_path, quiz_id):
    with get_connection(db_path) as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM question WHERE quiz_id = ?",
            (quiz_id,),
        ).fetchone()[0]


def create_empty_quiz(db_path):
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO quiz (lecturer_id, title, duration_minutes)
            VALUES (?, ?, ?)
            """,
            (1, "US03 Test Quiz", 30),
        )
        conn.commit()
        return cursor.lastrowid


def valid_form(**changes):
    form = {
        "content": "Which layer runs SQL queries?",
        "choices": [
            "Routes",
            "Services",
            "Repositories",
            "Templates",
        ],
        "correct_index": "2",
        "points": "1",
    }
    form.update(changes)
    return form


def add_question(client, quiz_id, **changes):
    return client.post(
        f"/quiz/{quiz_id}/questions",
        data=valid_form(**changes),
    )


def test_us03_01_add_valid_question(client, db_path):
    # US03-01
    quiz_id = create_empty_quiz(db_path)
    login(client)

    assert question_count(db_path, quiz_id) == 0

    response = add_question(client, quiz_id)

    assert response.status_code == 302
    assert question_count(db_path, quiz_id) == 1


def test_us03_02_save_four_choices(client, db_path):
    # US03-02
    quiz_id = create_empty_quiz(db_path)
    login(client)

    response = add_question(client, quiz_id)

    assert response.status_code == 302

    with get_connection(db_path) as conn:
        question = conn.execute(
            """
            SELECT question_id
            FROM question
            WHERE quiz_id = ?
            """,
            (quiz_id,),
        ).fetchone()

        choices = conn.execute(
            """
            SELECT content, is_correct
            FROM choice
            WHERE question_id = ?
            ORDER BY choice_id
            """,
            (question["question_id"],),
        ).fetchall()

    assert len(choices) == 4
    assert [row["content"] for row in choices] == [
        "Routes",
        "Services",
        "Repositories",
        "Templates",
    ]
    assert [row["is_correct"] for row in choices] == [
        0, 0, 1, 0
    ]


def test_us03_03_reject_missing_correct_answer(client, db_path):
    # US03-03
    quiz_id = create_empty_quiz(db_path)
    login(client)

    response = add_question(
        client,
        quiz_id,
        correct_index="",
    )

    assert response.status_code == 422
    assert SELECT_CORRECT_OPTION in response.get_data(as_text=True)
    assert question_count(db_path, quiz_id) == 0


def test_us03_04_reject_three_choices(client, db_path):
    # US03-04
    quiz_id = create_empty_quiz(db_path)
    login(client)

    response = add_question(
        client,
        quiz_id,
        choices=[
            "Routes",
            "Services",
            "Repositories",
            "",
        ],
    )

    assert response.status_code == 422
    assert CHOICES_REQUIRED in response.get_data(as_text=True)
    assert question_count(db_path, quiz_id) == 0


def test_us03_05_accept_four_choices(client, db_path):
    # US03-05
    quiz_id = create_empty_quiz(db_path)
    login(client)

    response = add_question(
        client,
        quiz_id,
        choices=["A", "B", "C", "D"],
    )

    assert response.status_code == 302
    assert question_count(db_path, quiz_id) == 1


def test_us03_06_reject_zero_points(client, db_path):
    # US03-06
    quiz_id = create_empty_quiz(db_path)
    login(client)

    response = add_question(
        client,
        quiz_id,
        points="0",
    )

    assert response.status_code == 422
    assert INVALID_POINTS in response.get_data(as_text=True)
    assert question_count(db_path, quiz_id) == 0


def test_us03_07_minimum_points_and_ownership(client, db_path):
    # US03-07
    quiz_id = create_empty_quiz(db_path)
    login(client)

    response = add_question(
        client,
        quiz_id,
        points="1",
    )

    assert response.status_code == 302
    assert question_count(db_path, quiz_id) == 1

    with get_connection(db_path) as conn:
        points = conn.execute(
            "SELECT points FROM question WHERE quiz_id = ?",
            (quiz_id,),
        ).fetchone()[0]

    assert points == 1

    client.post("/logout")

    login(client, "nam.lecturer@example.edu")

    forbidden = add_question(client, quiz_id)

    assert forbidden.status_code == 403
    assert NOT_QUIZ_OWNER in forbidden.get_data(as_text=True)
    assert question_count(db_path, quiz_id) == 1
