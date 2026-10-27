from __future__ import annotations
import pytest
from markupsafe import escape

from src.app import create_app
from src.db import get_connection
from src.repositories import question_repository
from src.errors import (
    CHOICES_REQUIRED,
    INVALID_POINTS,
    NOT_QUIZ_OWNER,
    QUESTION_CONTENT_REQUIRED,
    SELECT_CORRECT_OPTION,
)
from src.init_db import init_db

NGAN_QUIZ = 13
NAM_QUIZ = 14
NGAN_EMAIL = "ngan.lecturer@example.edu"
NAM_EMAIL = "nam.lecturer@example.edu"
STUDENT_EMAIL = "duc.student@example.edu"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms.db"
    init_db(path)
    return path


@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


def login(client, email=NGAN_EMAIL):
    response = client.post("/login", data={"email": email, "password": "MiniLMS2026!"})
    assert response.status_code == 302


def shows(response, text):
    return str(escape(text)) in response.get_data(as_text=True)


def count_rows(db_path, sql, params=()):
    with get_connection(db_path) as connection:
        return connection.execute(sql, params).fetchone()[0]


def question_count(db_path, quiz_id=NGAN_QUIZ):
    return count_rows(db_path, "SELECT COUNT(*) FROM question WHERE quiz_id = ?", (quiz_id,))


def valid_form(**changes):
    form = {
        "content": "Which layer runs the SQL queries?",
        "choices": ["Routes", "Services", "Repositories", "Templates"],
        "correct_index": "2",
        "points": "1",
    }
    form.update(changes)
    return form


def post_question(client, quiz_id=NGAN_QUIZ, **changes):
    return client.post(f"/quiz/{quiz_id}/questions", data=valid_form(**changes))


def make_empty_quiz(db_path):
    with get_connection(db_path) as connection:
        return connection.execute(
            "INSERT INTO quiz (lecturer_id, title, duration_minutes) VALUES (1, 'Empty quiz', 10)"
        ).lastrowid


def test_questions_route_redirects_to_integrated_manage_page(client):
    login(client)

    response = client.get(f"/quiz/{NGAN_QUIZ}/questions")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/lecturer/quiz/{NGAN_QUIZ}/publish")

    page = client.get(response.headers["Location"])
    html = page.get_data(as_text=True)
    assert page.status_code == 200
    assert "Manage Quiz" in html
    assert "Advanced Analytics" in html
    assert "Questions List" in html
    assert "Add Questions" in html
    assert html.count('type="radio"') == 8
    assert html.count('name="choices"') == 8
    assert 'class="correct-answer"' in html
    assert "Correct answer" in html
    assert "Sign out" not in html
    assert "Has correct answer" not in html
    assert "Missing correct answer" not in html
    assert '<details class="manage-disclosure card">' in html


def test_adding_first_question_makes_the_count_1(client, db_path):
    quiz_id = make_empty_quiz(db_path)
    login(client)
    manage_page = client.get(f"/lecturer/quiz/{quiz_id}/publish")
    assert "No questions have been added yet." in manage_page.get_data(as_text=True)

    response = post_question(client, quiz_id)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/lecturer/quiz/{quiz_id}/publish")
    assert question_count(db_path, quiz_id) == 1
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "1 question in this quiz" in page
    assert "Question added successfully." in page


def test_saved_question_has_exactly_4_options_and_1_correct(client, db_path):
    login(client)

    post_question(client)

    with get_connection(db_path) as connection:
        question = connection.execute(
            "SELECT question_id, content, points, position FROM question "
            "WHERE quiz_id = ? ORDER BY position DESC LIMIT 1",
            (NGAN_QUIZ,),
        ).fetchone()
        choices = connection.execute(
            "SELECT content, is_correct FROM choice WHERE question_id = ? ORDER BY choice_id",
            (question["question_id"],),
        ).fetchall()

    assert question["content"] == "Which layer runs the SQL queries?"
    assert question["points"] == 1
    assert question["position"] == 2
    assert [choice["content"] for choice in choices] == ["Routes", "Services", "Repositories", "Templates"]
    assert [choice["is_correct"] for choice in choices] == [0, 0, 1, 0]


def test_each_new_question_gets_the_next_position(client, db_path):
    login(client)

    post_question(client)
    post_question(client)

    with get_connection(db_path) as connection:
        positions = [
            row[0]
            for row in connection.execute(
                "SELECT position FROM question WHERE quiz_id = ? ORDER BY position", (NGAN_QUIZ,)
            )
        ]
    assert positions == [1, 2, 3]


def test_failed_choice_insert_rolls_back_the_question(client, db_path, monkeypatch):
    login(client)

    def fail_insert(connection, question_id, content, is_correct):
        assert connection.in_transaction
        assert question_id > 0
        assert content == "Routes"
        assert is_correct is False
        raise RuntimeError("Choice insert failed")

    monkeypatch.setattr(question_repository, "insert_choice", fail_insert)

    with pytest.raises(RuntimeError, match="Choice insert failed"):
        post_question(client)

    assert question_count(db_path) == 1
    assert count_rows(db_path, "SELECT COUNT(*) FROM choice") == 60


def test_missing_correct_option_shows_message_and_saves_nothing(client, db_path):
    login(client)
    before = question_count(db_path)

    response = client.post(
        f"/quiz/{NGAN_QUIZ}/questions",
        data={"content": "A question", "choices": ["a", "b", "c", "d"], "points": "1"},
    )

    assert response.status_code == 422
    assert shows(response, SELECT_CORRECT_OPTION)
    assert question_count(db_path) == before
    assert count_rows(db_path, "SELECT COUNT(*) FROM choice") == 60


def test_form_keeps_what_the_lecturer_typed_after_an_error(client):
    login(client)

    response = post_question(client, correct_index="")
    html = response.get_data(as_text=True)

    assert response.status_code == 422
    assert '<details class="manage-disclosure card" open>' in html
    assert "Which layer runs the SQL queries?" in html
    for text in ("Routes", "Services", "Repositories", "Templates"):
        assert f'value="{text}"' in html


@pytest.mark.parametrize("bad_index", ["", "4", "-1", "abc"])
def test_correct_option_must_be_one_of_the_four_options(client, db_path, bad_index):
    login(client)
    before = question_count(db_path)

    response = post_question(client, correct_index=bad_index)

    assert response.status_code == 422
    assert shows(response, SELECT_CORRECT_OPTION)
    assert question_count(db_path) == before


def test_empty_question_text_is_rejected(client, db_path):
    login(client)
    before = question_count(db_path)

    response = post_question(client, content="   ")

    assert response.status_code == 422
    assert shows(response, QUESTION_CONTENT_REQUIRED)
    assert question_count(db_path) == before


@pytest.mark.parametrize(
    "choices",
    [
        ["Routes", "Services", "Repositories", ""],
        ["Routes", "Services", "Repositories"],
        ["Routes", "Services", "Repositories", "   "],
    ],
)
def test_all_four_options_must_be_filled(client, db_path, choices):
    login(client)
    before = question_count(db_path)

    response = post_question(client, choices=choices)

    assert response.status_code == 422
    assert shows(response, CHOICES_REQUIRED)
    assert question_count(db_path) == before


@pytest.mark.parametrize(
    "bad_points",
    ["", "0", "-2", "1.5", "abc", "1_0", str(1 << 63)],
)
def test_points_must_be_a_positive_whole_number(client, db_path, bad_points):
    login(client)
    before = question_count(db_path)

    response = post_question(client, points=bad_points)

    assert response.status_code == 422
    assert shows(response, INVALID_POINTS)
    assert question_count(db_path) == before


def test_several_problems_are_all_shown_at_once(client):
    login(client)

    response = post_question(client, content="", correct_index="")

    assert shows(response, QUESTION_CONTENT_REQUIRED)
    assert shows(response, SELECT_CORRECT_OPTION)


@pytest.mark.parametrize("method", ["get", "post"])
def test_another_lecturer_cannot_edit_the_quiz(client, db_path, method):
    login(client, NAM_EMAIL)
    before = question_count(db_path)

    response = getattr(client, method)(
        f"/quiz/{NGAN_QUIZ}/questions",
        **({"data": valid_form()} if method == "post" else {}),
    )

    assert response.status_code == 403
    assert shows(response, NOT_QUIZ_OWNER)
    assert question_count(db_path) == before


def test_unknown_quiz_returns_404(client):
    login(client)

    assert client.get("/quiz/999/questions").status_code == 404
    assert post_question(client, quiz_id=999).status_code == 404


@pytest.mark.parametrize("method", ["get", "post"])
def test_student_gets_403(client, db_path, method):
    login(client, STUDENT_EMAIL)
    before = question_count(db_path)

    response = getattr(client, method)(f"/quiz/{NGAN_QUIZ}/questions")

    assert response.status_code == 403
    assert question_count(db_path) == before


@pytest.mark.parametrize("method", ["get", "post"])
def test_guest_is_redirected_to_login(client, method):
    response = getattr(client, method)(f"/quiz/{NGAN_QUIZ}/questions")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_question_text_is_escaped_in_the_page(client):
    login(client)

    post_question(client, content="<script>alert(1)</script>")
    html = client.get(f"/lecturer/quiz/{NGAN_QUIZ}/publish").get_data(as_text=True)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_lecturer_can_edit_question_choices_and_correct_answer(client, db_path):
    login(client)
    with get_connection(db_path) as connection:
        question_id = connection.execute(
            "SELECT question_id FROM question WHERE quiz_id = ? ORDER BY position LIMIT 1",
            (NGAN_QUIZ,),
        ).fetchone()[0]

    response = client.post(
        f"/quiz/{NGAN_QUIZ}/questions/{question_id}/edit",
        data=valid_form(
            content="Updated question text",
            choices=["Updated A", "Updated B", "Updated C", "Updated D"],
            correct_index="3",
        ),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Question updated successfully." in response.get_data(as_text=True)
    with get_connection(db_path) as connection:
        question = connection.execute(
            "SELECT content FROM question WHERE question_id = ?", (question_id,)
        ).fetchone()
        choices = connection.execute(
            "SELECT content, is_correct FROM choice WHERE question_id = ? ORDER BY choice_id",
            (question_id,),
        ).fetchall()
    assert question["content"] == "Updated question text"
    assert [(row["content"], row["is_correct"]) for row in choices] == [
        ("Updated A", 0),
        ("Updated B", 0),
        ("Updated C", 0),
        ("Updated D", 1),
    ]


def test_invalid_question_edit_keeps_the_form_open_and_preserves_values(client, db_path):
    login(client)
    with get_connection(db_path) as connection:
        question_id = connection.execute(
            "SELECT question_id FROM question WHERE quiz_id = ? ORDER BY position LIMIT 1",
            (NGAN_QUIZ,),
        ).fetchone()[0]

    response = client.post(
        f"/quiz/{NGAN_QUIZ}/questions/{question_id}/edit",
        data=valid_form(content="", correct_index=""),
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 422
    assert '<details class="manage-disclosure card" open>' in html
    assert f'<details class="manage-edit-disclosure" open>' in html
    assert shows(response, QUESTION_CONTENT_REQUIRED)
    assert shows(response, SELECT_CORRECT_OPTION)
    assert 'value="Routes"' in html


def test_lecturer_cannot_edit_another_quiz_question(client):
    login(client, NAM_EMAIL)

    response = client.post(
        f"/quiz/{NGAN_QUIZ}/questions/1/edit",
        data=valid_form(),
    )

    assert response.status_code == 403
