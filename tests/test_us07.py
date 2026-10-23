import re

import pytest

from src.db import get_connection
from tests.test_attempt import (
    PUBLISHED_QUIZ,
    answer,
    checked_value,
    choice_ids,
    client,
    db_path,
    login,
    question_ids,
)

# US07: answer and review a quiz


@pytest.fixture
def ten_question_client(db_path, client):
    """Quiz 1 with ten questions; the extra nine exist only in this test database."""
    with get_connection(db_path) as connection:
        for position in range(2, 11):
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


def start_quiz(client):
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")


def marked_answered(html, number):
    return re.search(rf'value="{number}"\s+class="answered"', html) is not None


def answer_all_except(client, db_path, skipped):
    """Answer every question of quiz 1 with choice B, except question number `skipped`."""
    for number, question_id in enumerate(question_ids(db_path), start=1):
        if number != skipped:
            answer(client, db_path, question_id, choice_ids(db_path, question_id)[1], go=1)


def test_choice_b_on_question_7_stays_answered_after_moving_to_question_8(ten_question_client, db_path):
    """AC1: Given a quiz has 10 questions, when the student selects choice B for question 7
    and moves to question 8, then question 7 remains marked as answered with choice B."""
    client = ten_question_client
    start_quiz(client)
    question_7 = question_ids(db_path)[6]
    choice_b = choice_ids(db_path, question_7)[1]

    response = answer(client, db_path, question_7, choice_b, go=8)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("take?q=8")
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Question 8 / 10" in page
    assert marked_answered(page, 7)
    assert not marked_answered(page, 8)
    assert "checked" not in page

    page = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=7").get_data(as_text=True)
    assert "Question 7 / 10" in page
    assert checked_value(choice_b) in page
    assert page.count("checked") == 1

    with get_connection(db_path) as connection:
        rows = connection.execute("SELECT question_id, choice_id FROM answer").fetchall()
    assert [tuple(row) for row in rows] == [(question_7, choice_b)]


def test_review_lists_question_7_as_unanswered(ten_question_client, db_path):
    """AC2: Given question 7 is unanswered, when the student opens the review,
    then the review lists Question 7 under unanswered questions."""
    client = ten_question_client
    start_quiz(client)
    answer_all_except(client, db_path, skipped=7)

    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/review")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "You answered 9 of 10 questions" in html
    assert "Unanswered questions" in html
    assert re.findall(r"<li>Question (\d+)", html) == ["7"]
    assert f'href="/student/quiz/{PUBLISHED_QUIZ}/take?q=7"' in html
    assert 'name="confirm"' in html


def test_answering_question_7_from_review_clears_unanswered_list(ten_question_client, db_path):
    """Story goal: after the review lists Question 7 as unanswered, the student can go back,
    answer it, and the review then shows no unanswered questions."""
    client = ten_question_client
    start_quiz(client)
    answer_all_except(client, db_path, skipped=7)
    assert client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=7").status_code == 200
    question_7 = question_ids(db_path)[6]

    response = answer(client, db_path, question_7, choice_ids(db_path, question_7)[1], go="review")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/student/quiz/{PUBLISHED_QUIZ}/review")
    html = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "You answered 10 of 10 questions" in html
    assert "Unanswered questions" not in html
    assert 'name="confirm"' not in html
