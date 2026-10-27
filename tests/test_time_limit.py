from datetime import datetime, timedelta, timezone
import re

import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db
from src.services.quiz_service import InvalidQuiz, create_new_quiz
import src.services.attempt_service as attempt_service


QUIZ_ID = 1
LECTURER_ID = 1
STUDENT_ID = 3
# Fixed clock, independent of today's date.
START = datetime(2026, 10, 17, 8, 0, 0)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "us11.db"
    init_db(path)
    with get_connection(path) as conn:
        conn.execute(
            """
            UPDATE quiz
               SET status = 'published',
                   duration_minutes = 30,
                   duration_unlimited = 0,
                   start_at = NULL,
                   end_at = NULL
             WHERE quiz_id = ?
            """,
            (QUIZ_ID,),
        )
    return path

@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    client = app.test_client()
    # No dependency on checked-in demo passwords.
    with client.session_transaction() as session:
        session["user_id"] = STUDENT_ID
        session["role"] = "student"
    return client


def _remaining(response):
    html = response.get_data(as_text=True)
    match = re.search(r'data-remaining="(\d+)"', html)
    assert match is not None, "Missing countdown data-remaining in quiz HTML"
    return int(match.group(1))


def _attempt(db_path):
    with get_connection(db_path) as conn:
        return conn.execute(
            """
            SELECT attempt_id, started_at, submitted_at
              FROM attempt
             WHERE student_id = ? AND quiz_id = ?
             ORDER BY attempt_id DESC LIMIT 1
            """,
            (STUDENT_ID, QUIZ_ID),
        ).fetchone()


def _set_clock(monkeypatch, current):
    """Match the application's clock function; fail visibly if renamed."""
    monkeypatch.setattr(attempt_service, "_now", lambda: current)


def test_tc11_01_countdown_starts_at_30_minutes(client, monkeypatch):
    """TC11-01 / AC1: A 30-minute quiz starts near 30:00."""
    _set_clock(monkeypatch, START)
    response = client.post(f"/student/quiz/{QUIZ_ID}/start")
    assert response.status_code == 302

    page = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")
    assert page.status_code == 200
    assert _remaining(page) == 1800


def test_tc11_02_expired_attempt_is_submitted_once(client, db_path, monkeypatch):
    """TC11-02 / AC2: Time expiry submits, without duplicate submissions."""
    _set_clock(monkeypatch, START)
    assert client.post(f"/student/quiz/{QUIZ_ID}/start").status_code == 302
    initial = _attempt(db_path)
    assert initial is not None and initial["submitted_at"] is None

    _set_clock(monkeypatch, START + timedelta(minutes=30))
    response = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")
    assert response.status_code == 302
    assert "submitted" in response.headers["Location"]

    submitted = _attempt(db_path)
    assert submitted["attempt_id"] == initial["attempt_id"]
    assert submitted["submitted_at"] is not None

    client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")
    again = _attempt(db_path)
    assert again["attempt_id"] == submitted["attempt_id"]
    assert again["submitted_at"] == submitted["submitted_at"]


@pytest.mark.parametrize("duration", ["0", "-1", "-5"])
def test_tc11_03_nonpositive_duration_rejected(db_path, duration):
    """TC11-03 / AC3: Zero and negative time limits must be rejected."""
    with get_connection(db_path) as conn:
        before = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]

    with pytest.raises(InvalidQuiz):
        create_new_quiz(
            db_path,
            lecturer_id=LECTURER_ID,
            title="Invalid duration",
            duration=duration,
        )

    with get_connection(db_path) as conn:
        after = conn.execute("SELECT COUNT(*) FROM quiz").fetchone()[0]
    assert after == before


def test_tc11_04_refresh_preserves_12_minutes(client, db_path, monkeypatch):
    """TC11-04 / AC4: Refresh at 12:00 does not reset time to 30:00."""
    _set_clock(monkeypatch, START)
    assert client.post(f"/student/quiz/{QUIZ_ID}/start").status_code == 302
    initial = _attempt(db_path)
    assert initial is not None

    _set_clock(monkeypatch, START + timedelta(minutes=18))
    first = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")
    refreshed = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")

    assert first.status_code == refreshed.status_code == 200
    assert 0 < _remaining(first) <= 720
    assert 0 < _remaining(refreshed) <= 720
    assert _attempt(db_path)["attempt_id"] == initial["attempt_id"]


def test_tc11_05_attempt_is_active_one_second_before_deadline(
    client, db_path, monkeypatch
):
    """TC11-05: At 29:59, the attempt remains active with about one second left."""
    _set_clock(monkeypatch, START)
    assert client.post(f"/student/quiz/{QUIZ_ID}/start").status_code == 302

    _set_clock(monkeypatch, START + timedelta(minutes=29, seconds=59))
    response = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")

    assert response.status_code == 200
    assert _remaining(response) == 1
    assert _attempt(db_path)["submitted_at"] is None


def test_tc11_06_expired_attempt_is_submitted_and_cannot_answer(
    client, db_path, monkeypatch
):
    """TC11-06: At 30:01, the attempt is submitted and answering is rejected."""
    _set_clock(monkeypatch, START)
    assert client.post(f"/student/quiz/{QUIZ_ID}/start").status_code == 302
    initial = _attempt(db_path)
    assert initial is not None

    with get_connection(db_path) as conn:
        question = conn.execute(
            "SELECT question_id FROM question WHERE quiz_id = ? LIMIT 1",
            (QUIZ_ID,),
        ).fetchone()
        choice = conn.execute(
            """
            SELECT c.choice_id
              FROM choice c
              JOIN question q ON q.question_id = c.question_id
             WHERE q.quiz_id = ? LIMIT 1
            """,
            (QUIZ_ID,),
        ).fetchone()
    assert question is not None and choice is not None

    _set_clock(monkeypatch, START + timedelta(minutes=30, seconds=1))
    expired_page = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")
    assert expired_page.status_code == 302
    assert "submitted" in expired_page.headers["Location"]

    submitted = _attempt(db_path)
    assert submitted["attempt_id"] == initial["attempt_id"]
    assert submitted["submitted_at"] is not None

    answer = client.post(
        f"/student/quiz/{QUIZ_ID}/take",
        data={
            "attempt_id": submitted["attempt_id"],
            "question_id": question["question_id"],
            "choice_id": choice["choice_id"],
            "go": "1",
        },
    )
    assert answer.status_code == 409
    assert _attempt(db_path)["submitted_at"] == submitted["submitted_at"]
