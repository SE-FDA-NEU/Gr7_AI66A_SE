from datetime import datetime, timedelta
import re

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
    AUTO_SUBMITTED,
    UNANSWERED_NOT_CONFIRMED,
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
    with get_connection(path) as connection:
        connection.execute("UPDATE quiz SET start_at = NULL, end_at = NULL")
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


def submitted_row(db_path, student_id=DUC_ID, quiz_id=PUBLISHED_QUIZ):
    with get_connection(db_path) as connection:
        row = connection.execute(
            "SELECT submitted_at, score FROM attempt WHERE student_id = ? AND quiz_id = ?",
            (student_id, quiz_id),
        ).fetchone()
    return tuple(row)


def submit(client, db_path, confirm=False):
    data = {"attempt_id": open_attempt_id(db_path)}
    if confirm:
        data["confirm"] = "yes"
    return client.post(f"/student/quiz/{PUBLISHED_QUIZ}/submit", data=data)


def checked_value(choice_id):
    return rf'value="{choice_id}"\s+checked'


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
    assert re.search(checked_value(choice_id), html)
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


def test_us13_take_page_contains_one_time_second_tab_warning(client):
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'id="anti-cheat-warning"' in html
    assert 'Warning recorded: you left the quiz page or opened another tab.' in html
    assert 'document.addEventListener("visibilitychange"' in html
    assert 'window.addEventListener("blur", recordWarning)' in html


def test_late_answer_is_not_saved_and_attempt_is_auto_submitted(client, db_path, monkeypatch):
    start = datetime(2026, 10, 17, 8, 0, 0)
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    question_id = question_ids(db_path)[0]

    # Quiz 1 lasts 20 minutes.
    monkeypatch.setattr(attempt_service, "_now", lambda: start + timedelta(minutes=20))
    response = answer(client, db_path, question_id, choice_ids(db_path, question_id)[0], go=1)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/student/quiz/{PUBLISHED_QUIZ}/submitted?timeout=1")
    assert count_rows(db_path, "SELECT COUNT(*) FROM answer") == 0
    assert submitted_row(db_path) == ("2026-10-17T08:20:00", 0.0)


def test_starting_before_the_scheduled_window_is_rejected(client, db_path, monkeypatch):
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET start_at = ?, end_at = ? WHERE quiz_id = ?",
            ("2026-10-17T04:00:00", "2026-10-17T05:00:00", PUBLISHED_QUIZ),
        )
    monkeypatch.setattr(attempt_service, "_now", lambda: datetime(2026, 10, 17, 3, 59, 0))
    login(client)

    response = client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    assert response.status_code == 403
    assert shows_message(response, "This quiz is not open yet.")
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt") == 0


def test_quiz_end_time_caps_attempt_and_auto_submits_at_the_schedule_deadline(
    client, db_path, monkeypatch
):
    start = datetime(2026, 10, 17, 4, 30, 0)
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET duration_minutes = 60, start_at = ?, end_at = ? WHERE quiz_id = ?",
            ("2026-10-17T04:00:00", "2026-10-17T05:00:00", PUBLISHED_QUIZ),
        )
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    take_page = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")
    take_html = take_page.get_data(as_text=True)
    assert 'data-remaining="1800"' in take_html
    assert '<div class="quiz-heading-row">' in take_html
    assert '<p class="timer">Time left:' in take_html

    monkeypatch.setattr(attempt_service, "_now", lambda: datetime(2026, 10, 17, 5, 0, 0))
    question_id = question_ids(db_path)[0]
    response = answer(client, db_path, question_id, choice_ids(db_path, question_id)[0], go=1)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        f"/student/quiz/{PUBLISHED_QUIZ}/submitted?timeout=1"
    )
    assert submitted_row(db_path) == ("2026-10-17T05:00:00", 0.0)


def test_remaining_seconds_counts_down_from_duration():
    start = "2026-10-17T08:00:00"

    assert attempt_service.remaining_seconds(start, 20, datetime(2026, 10, 17, 8, 0, 0)) == 1200
    assert attempt_service.remaining_seconds(start, 20, datetime(2026, 10, 17, 8, 5, 30)) == 870
    assert attempt_service.remaining_seconds(start, 20, datetime(2026, 10, 17, 9, 0, 0)) == 0
    assert attempt_service.remaining_seconds(
        start,
        60,
        datetime(2026, 10, 17, 8, 30, 0),
        end_at="2026-10-17T08:30:00",
    ) == 0
    assert attempt_service.remaining_seconds(
        start,
        None,
        datetime(2026, 10, 17, 8, 5, 0),
    ) is None
    assert attempt_service.remaining_seconds(
        start,
        None,
        datetime(2026, 10, 17, 8, 5, 0),
        end_at="2026-10-17T08:30:00",
    ) == 1500


def test_unlimited_attempt_without_deadline_has_no_timer_or_auto_submission(
    client, db_path, monkeypatch
):
    start = datetime(2026, 10, 17, 8, 0, 0)
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET duration_unlimited = 1, end_at = NULL WHERE quiz_id = ?",
            (PUBLISHED_QUIZ,),
        )
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    monkeypatch.setattr(attempt_service, "_now", lambda: start + timedelta(days=30))
    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")

    assert response.status_code == 200
    assert "No time limit" in response.get_data(as_text=True)
    assert 'id="timer"' not in response.get_data(as_text=True)
    assert submitted_row(db_path)[0] is None


def test_unlimited_duration_still_auto_submits_at_deadline(client, db_path, monkeypatch):
    start = datetime(2026, 10, 17, 8, 0, 0)
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET duration_unlimited = 1, end_at = ? WHERE quiz_id = ?",
            ("2026-10-17T08:30:00", PUBLISHED_QUIZ),
        )
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    page = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")
    assert 'data-remaining="1800"' in page.get_data(as_text=True)
    monkeypatch.setattr(attempt_service, "_now", lambda: start + timedelta(minutes=30))

    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        f"/student/quiz/{PUBLISHED_QUIZ}/submitted?timeout=1"
    )
    assert submitted_row(db_path)[0] == "2026-10-17T08:30:00"


def test_next_and_previous_keep_the_saved_answer(multi_question_client, db_path):
    client = multi_question_client
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    first_question, second_question, _ = question_ids(db_path)
    chosen = choice_ids(db_path, first_question)[1]

    page = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1").get_data(as_text=True)
    assert "Question 1 / 3" in page
    assert page.count('name="go"') == 5  # Next + jump buttons 1..3 + Review & submit

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
    assert re.search(checked_value(chosen), page)


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


# US08: review and submit


def start_and_answer(client, db_path, answers):
    """Start quiz 1 and answer {question_number: choice_index}."""
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    ids = question_ids(db_path)
    for number, choice_index in answers.items():
        question_id = ids[number - 1]
        answer(client, db_path, question_id, choice_ids(db_path, question_id)[choice_index], go=1)


def test_review_lists_unanswered_questions(multi_question_client, db_path):
    client = multi_question_client
    start_and_answer(client, db_path, {1: 0, 3: 0})

    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/review")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "You answered 2 of 3 questions" in html
    assert "Question 2" in html
    assert f'href="/student/quiz/{PUBLISHED_QUIZ}/take?q=2"' in html
    assert "Question 1" not in html
    assert "Question 3" not in html
    assert 'name="confirm"' in html
    assert 'data-confirm="Are you sure you want to submit this quiz?' in html


def test_review_without_unanswered_questions_needs_no_confirmation(client, db_path):
    start_and_answer(client, db_path, {1: 0})

    html = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/review").get_data(as_text=True)

    assert "You answered 1 of 1 questions" in html
    assert "Unanswered questions" not in html
    assert 'name="confirm"' not in html


def test_review_and_submit_button_saves_answer_then_opens_review(client, db_path):
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    question_id = question_ids(db_path)[0]

    response = answer(client, db_path, question_id, choice_ids(db_path, question_id)[0], go="review")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/student/quiz/{PUBLISHED_QUIZ}/review")
    assert count_rows(db_path, "SELECT COUNT(*) FROM answer") == 1
    take_page = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1").get_data(as_text=True)
    assert "Review &amp; submit" in take_page
    assert 'class="quiz-controls"' in take_page
    assert 'class="quiz-submit-actions"' in take_page
    assert 'class="quiz-heading-row"' in take_page
    assert 'class="timer"' in take_page
    assert 'class="btn btn-secondary" href="/student/dashboard">Back to dashboard</a>' in take_page
    assert 'class="quiz-question-layout"' in take_page
    assert 'class="question-prompt" id="question-prompt"' in take_page
    assert 'class="jump" aria-label="Jump to question"' in take_page


def test_submit_stores_submission_time_and_score(client, db_path):
    start_and_answer(client, db_path, {1: 0})  # first choice is the correct one

    response = submit(client, db_path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/student/quiz/{PUBLISHED_QUIZ}/submitted")
    submitted_at, score = submitted_row(db_path)
    assert submitted_at is not None
    assert score == 1.0
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Quiz submitted" in page
    assert "Your quiz was submitted successfully." in page
    assert "Submitted at" in page
    assert 'class="btn btn-secondary" href="/student/dashboard">Back to dashboard</a>' in page


def test_student_can_take_up_to_the_quiz_attempt_limit(client, db_path):
    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET max_attempts = 2 WHERE quiz_id = ?",
            (PUBLISHED_QUIZ,),
        )

    start_and_answer(client, db_path, {1: 0})
    assert submit(client, db_path).status_code == 302

    start_and_answer(client, db_path, {1: 0})
    assert submit(client, db_path).status_code == 302

    response = client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")
    assert response.status_code == 409
    assert shows_message(response, ALREADY_SUBMITTED)
    assert count_rows(
        db_path,
        "SELECT COUNT(*) FROM attempt WHERE student_id = ? AND quiz_id = ? AND submitted_at IS NOT NULL",
        (DUC_ID, PUBLISHED_QUIZ),
    ) == 2


def test_submitted_page_shows_vietnam_time(client, db_path, monkeypatch):
    monkeypatch.setattr(attempt_service, "_now", lambda: datetime(2026, 10, 18, 8, 0, 0))
    start_and_answer(client, db_path, {1: 0})
    monkeypatch.setattr(attempt_service, "_now", lambda: datetime(2026, 10, 18, 8, 15, 0))

    response = submit(client, db_path)

    assert submitted_row(db_path)[0] == "2026-10-18T08:15:00"
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Submitted at 18 Oct 2026, 15:15 (UTC+7)" in page


def test_vietnam_time_crosses_midnight():
    assert attempt_service.format_vietnam_time("2026-10-18T20:30:00") == "19 Oct 2026, 03:30 (UTC+7)"


def test_score_is_correct_answers_over_total_questions(multi_question_client, db_path):
    client = multi_question_client
    start_and_answer(client, db_path, {1: 0, 2: 1, 3: 0})  # Q2 wrong

    submit(client, db_path)

    assert submitted_row(db_path)[1] == pytest.approx(2 / 3)


def test_unanswered_questions_require_confirmation(multi_question_client, db_path):
    client = multi_question_client
    start_and_answer(client, db_path, {1: 0, 3: 0})

    response = submit(client, db_path)

    assert response.status_code == 422
    assert shows_message(response, UNANSWERED_NOT_CONFIRMED)
    assert "Question 2" in response.get_data(as_text=True)
    assert submitted_row(db_path)[0] is None

    response = submit(client, db_path, confirm=True)

    assert response.status_code == 302
    assert submitted_row(db_path)[1] == pytest.approx(2 / 3)


def test_second_submission_is_rejected(client, db_path):
    start_and_answer(client, db_path, {1: 0})
    attempt_id = open_attempt_id(db_path)
    submit(client, db_path)
    first = submitted_row(db_path)

    response = client.post(f"/student/quiz/{PUBLISHED_QUIZ}/submit", data={"attempt_id": attempt_id})

    assert response.status_code == 409
    assert shows_message(response, ALREADY_SUBMITTED)
    assert submitted_row(db_path) == first
    assert count_rows(db_path, "SELECT COUNT(*) FROM attempt WHERE submitted_at IS NOT NULL") == 1


def test_answers_cannot_change_after_submission(client, db_path):
    start_and_answer(client, db_path, {1: 0})
    attempt_id = open_attempt_id(db_path)
    submit(client, db_path)
    question_id = question_ids(db_path)[0]
    original, other = choice_ids(db_path, question_id)[:2]

    response = client.post(
        f"/student/quiz/{PUBLISHED_QUIZ}/take",
        data={"attempt_id": attempt_id, "question_id": question_id, "choice_id": other, "go": 1},
    )

    assert response.status_code == 409
    assert shows_message(response, ALREADY_SUBMITTED)
    with get_connection(db_path) as connection:
        stored = connection.execute("SELECT choice_id FROM answer").fetchall()
    assert [row[0] for row in stored] == [original]
    assert submitted_row(db_path)[1] == 1.0
    assert client.get(f"/student/quiz/{PUBLISHED_QUIZ}/take?q=1").status_code == 409


@pytest.mark.parametrize("page", ["take?q=1", "review"])
def test_expired_attempt_is_auto_submitted_when_page_is_opened(client, db_path, monkeypatch, page):
    start = datetime(2026, 10, 18, 8, 0, 0)
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    start_and_answer(client, db_path, {1: 0})

    # Quiz 1 lasts 20 minutes; the student comes back 5 minutes after it ran out.
    monkeypatch.setattr(attempt_service, "_now", lambda: start + timedelta(minutes=25))
    response = client.get(f"/student/quiz/{PUBLISHED_QUIZ}/{page}")

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/student/quiz/{PUBLISHED_QUIZ}/submitted?timeout=1")
    assert submitted_row(db_path) == ("2026-10-18T08:20:00", 1.0)
    result = client.get(response.headers["Location"])
    assert shows_message(result, AUTO_SUBMITTED)
    assert "Submitted at 18 Oct 2026, 15:20 (UTC+7)" in result.get_data(as_text=True)


def test_expired_attempt_is_auto_submitted_on_submit_without_confirmation(
    multi_question_client, db_path, monkeypatch
):
    client = multi_question_client
    start = datetime(2026, 10, 18, 8, 0, 0)
    monkeypatch.setattr(attempt_service, "_now", lambda: start)
    start_and_answer(client, db_path, {1: 0})

    monkeypatch.setattr(attempt_service, "_now", lambda: start + timedelta(minutes=20))
    response = submit(client, db_path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("submitted?timeout=1")
    assert submitted_row(db_path)[1] == pytest.approx(1 / 3)


def test_submitted_page_before_submitting_shows_404(client, db_path):
    login(client)
    client.post(f"/student/quiz/{PUBLISHED_QUIZ}/start")

    assert client.get(f"/student/quiz/{PUBLISHED_QUIZ}/submitted").status_code == 404


US08_ROUTES = [
    ("get", f"/student/quiz/{PUBLISHED_QUIZ}/review"),
    ("post", f"/student/quiz/{PUBLISHED_QUIZ}/submit"),
    ("get", f"/student/quiz/{PUBLISHED_QUIZ}/submitted"),
]


@pytest.mark.parametrize(("method", "path"), US08_ROUTES)
def test_unauthenticated_review_and_submit_redirect_to_login(client, method, path):
    response = getattr(client, method)(path)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


@pytest.mark.parametrize(("method", "path"), US08_ROUTES)
def test_lecturer_cannot_review_or_submit(client, method, path):
    login(client, "ngan.lecturer@example.edu")

    assert getattr(client, method)(path).status_code == 403


def test_student_cannot_submit_another_students_attempt(client, db_path):
    with get_connection(db_path) as connection:
        lan_attempt = connection.execute(
            "INSERT INTO attempt (student_id, quiz_id, started_at) VALUES (?, ?, ?)",
            (LAN_ID, PUBLISHED_QUIZ, attempt_service._now().strftime("%Y-%m-%dT%H:%M:%S")),
        ).lastrowid
    login(client)

    response = client.post(
        f"/student/quiz/{PUBLISHED_QUIZ}/submit",
        data={"attempt_id": lan_attempt, "confirm": "yes"},
    )

    assert response.status_code == 403
    assert shows_message(response, NOT_YOUR_ATTEMPT)
    assert submitted_row(db_path, student_id=LAN_ID)[0] is None
