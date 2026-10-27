import re

import pytest

import src.services.attempt_service as attempt_service
from src.db import get_connection
from src.errors import ALREADY_SUBMITTED, INVALID_CHOICE, QUESTION_NOT_FOUND
from src.services.attempt_service import AttemptError, UnansweredNotConfirmed
from tests.test_attempt import (
    DUC_ID,
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
def ten_question_db(db_path):
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
    return db_path


@pytest.fixture
def ten_question_client(ten_question_db, client):
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
    assert re.search(checked_value(choice_b), page)
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


# Service-level tests: call attempt_service directly, no Flask client.
# Expected values come from requirements.md (US06-US08, BR5, BR6), the status codes
# in design.md and the messages in src/errors.py.

LETTERS = "ABCD"


def start_attempt_id(db_path):
    return attempt_service.start_attempt(db_path, DUC_ID, PUBLISHED_QUIZ)["attempt_id"]


def choice_for(db_path, number, letter):
    """Choice id of option `letter` (A-D) for question `number` (1-based)."""
    question_id = question_ids(db_path)[number - 1]
    return question_id, choice_ids(db_path, question_id)[LETTERS.index(letter)]


def save(db_path, attempt_id, number, letter):
    question_id, choice_id = choice_for(db_path, number, letter)
    attempt_service.save_answer(db_path, DUC_ID, PUBLISHED_QUIZ, attempt_id, question_id, choice_id)


def answer_rows(db_path, attempt_id):
    with get_connection(db_path) as connection:
        rows = connection.execute(
            "SELECT question_id, choice_id FROM answer WHERE attempt_id = ? ORDER BY question_id",
            (attempt_id,),
        ).fetchall()
    return [tuple(row) for row in rows]


def answer_all_but(db_path, attempt_id, skipped):
    for number in range(1, 11):
        if number not in skipped:
            save(db_path, attempt_id, number, "B")


@pytest.mark.parametrize("question_number", [1, 10])
def test_take_page_accepts_first_and_last_question(ten_question_db, question_number):
    """US07-05/06 (BVA): q=1 and q=10 are the valid edges of a 10-question quiz."""
    # Arrange
    start_attempt_id(ten_question_db)

    # Act
    data = attempt_service.get_take_page_data(ten_question_db, DUC_ID, PUBLISHED_QUIZ, question_number)

    # Assert
    assert data["question_number"] == question_number
    assert data["total_questions"] == 10
    assert data["question"]["question_id"] == question_ids(ten_question_db)[question_number - 1]


@pytest.mark.parametrize("question_number", [0, 11])
def test_take_page_rejects_question_outside_quiz(ten_question_db, question_number):
    """US07-04/07 (BVA): q=0 and q=11 are just outside 1..10, so 404 QUESTION_NOT_FOUND."""
    # Arrange
    start_attempt_id(ten_question_db)

    # Act
    with pytest.raises(AttemptError, match=re.escape(QUESTION_NOT_FOUND)) as error:
        attempt_service.get_take_page_data(ten_question_db, DUC_ID, PUBLISHED_QUIZ, question_number)

    # Assert
    assert error.value.status_code == 404


UNANSWERED_CASES = [
    pytest.param(set(), [], id="0-unanswered"),
    pytest.param({7}, [7], id="1-unanswered-question-7"),
    pytest.param(set(range(1, 11)), list(range(1, 11)), id="10-unanswered"),
]


@pytest.mark.parametrize(("skipped", "unanswered"), UNANSWERED_CASES)
def test_review_unanswered_boundaries(ten_question_db, skipped, unanswered):
    """US07-08..10 (BVA, AC2): the review lists exactly the skipped question numbers."""
    # Arrange
    attempt_id = start_attempt_id(ten_question_db)
    answer_all_but(ten_question_db, attempt_id, skipped)

    # Act
    review = attempt_service.get_review_data(ten_question_db, DUC_ID, PUBLISHED_QUIZ)

    # Assert
    assert review["total_questions"] == 10
    assert review["unanswered_numbers"] == unanswered
    assert review["answered_count"] == 10 - len(unanswered)


def test_submit_without_unanswered_needs_no_confirmation(ten_question_db):
    """US07-11 (BVA, US08 AC2): 0 unanswered questions, so submitting unconfirmed succeeds."""
    # Arrange
    attempt_id = start_attempt_id(ten_question_db)
    answer_all_but(ten_question_db, attempt_id, skipped=set())

    # Act
    attempt_service.submit_attempt(ten_question_db, DUC_ID, PUBLISHED_QUIZ, attempt_id, confirmed=False)

    # Assert
    with get_connection(ten_question_db) as connection:
        submitted_at = connection.execute(
            "SELECT submitted_at FROM attempt WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()[0]
    assert submitted_at is not None


@pytest.mark.parametrize(("skipped", "unanswered"), UNANSWERED_CASES[1:])
def test_submit_with_unanswered_needs_confirmation(ten_question_db, skipped, unanswered):
    """US07-12/13 (BVA, US08 AC2): 1 or 10 unanswered questions need explicit confirmation."""
    # Arrange
    attempt_id = start_attempt_id(ten_question_db)
    answer_all_but(ten_question_db, attempt_id, skipped)

    # Act
    with pytest.raises(UnansweredNotConfirmed) as pending:
        attempt_service.submit_attempt(ten_question_db, DUC_ID, PUBLISHED_QUIZ, attempt_id, confirmed=False)

    # Assert
    assert pending.value.review["unanswered_numbers"] == unanswered


def test_choice_from_another_question_is_rejected(ten_question_db):
    """US07-14 (invalid partition): a choice of question 8 sent for question 7 is 400 and not saved."""
    # Arrange
    attempt_id = start_attempt_id(ten_question_db)
    question_7, _ = choice_for(ten_question_db, 7, "B")
    _, choice_of_question_8 = choice_for(ten_question_db, 8, "B")

    # Act
    with pytest.raises(AttemptError, match=re.escape(INVALID_CHOICE)) as error:
        attempt_service.save_answer(
            ten_question_db, DUC_ID, PUBLISHED_QUIZ, attempt_id, question_7, choice_of_question_8
        )

    # Assert
    assert error.value.status_code == 400
    assert answer_rows(ten_question_db, attempt_id) == []


def test_answer_cannot_change_after_submission(ten_question_db):
    """US07-15 (invalid partition, BR5/BR6): after submitting, changing question 7 is 409."""
    # Arrange
    attempt_id = start_attempt_id(ten_question_db)
    answer_all_but(ten_question_db, attempt_id, skipped=set())  # question 7 = B
    attempt_service.submit_attempt(ten_question_db, DUC_ID, PUBLISHED_QUIZ, attempt_id, confirmed=False)
    before = answer_rows(ten_question_db, attempt_id)

    # Act
    with pytest.raises(AttemptError, match=re.escape(ALREADY_SUBMITTED)) as error:
        save(ten_question_db, attempt_id, 7, "C")

    # Assert
    assert error.value.status_code == 409
    assert answer_rows(ten_question_db, attempt_id) == before
    assert choice_for(ten_question_db, 7, "B") in before


def test_changing_question_7_from_b_to_c_keeps_one_row(ten_question_db):
    """US07-16 (valid partition, AC1): changing question 7 from B to C updates the same row."""
    # Arrange
    attempt_id = start_attempt_id(ten_question_db)
    save(ten_question_db, attempt_id, 7, "B")

    # Act
    save(ten_question_db, attempt_id, 7, "C")

    # Assert
    assert answer_rows(ten_question_db, attempt_id) == [choice_for(ten_question_db, 7, "C")]
