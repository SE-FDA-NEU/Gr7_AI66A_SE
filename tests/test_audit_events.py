"""US12: the attempt service writes the append-only audit history."""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

import src.services.attempt_service as attempt_service
from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

QUIZ_ID = 1
STUDENT_ID = 3
START = datetime(2026, 10, 31, 8, 0, 0)  # fixed clock: tests never depend on today's date
DURATION = timedelta(minutes=20)  # seeded duration of quiz 1


@pytest.fixture
def clock(monkeypatch):
    state = {"now": START}
    monkeypatch.setattr(attempt_service, "_now", lambda: state["now"])
    return state


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms_test.db"
    init_db(path)
    with get_connection(path) as connection:
        connection.execute("UPDATE quiz SET start_at = NULL, end_at = NULL")
    return path


@pytest.fixture
def client(db_path, clock):
    app = create_app({"TESTING": True, "DATABASE_PATH": str(db_path)})
    return app.test_client()


def login(client, email="duc.student@example.edu"):
    client.post("/logout")
    response = client.post("/login", data={"email": email, "password": "MiniLMS2026!"})
    assert response.status_code == 302


def start(client, db_path):
    assert client.post(f"/student/quiz/{QUIZ_ID}/start").status_code == 302
    with get_connection(db_path) as connection:
        return connection.execute(
            "SELECT attempt_id FROM attempt WHERE student_id = ? AND quiz_id = ? "
            "AND submitted_at IS NULL",
            (STUDENT_ID, QUIZ_ID),
        ).fetchone()[0]


def first_question_and_choice(db_path):
    with get_connection(db_path) as connection:
        question_id = connection.execute(
            "SELECT question_id FROM question WHERE quiz_id = ? ORDER BY position LIMIT 1",
            (QUIZ_ID,),
        ).fetchone()[0]
        choices = [
            row[0]
            for row in connection.execute(
                "SELECT choice_id FROM choice WHERE question_id = ? ORDER BY choice_id",
                (question_id,),
            )
        ]
    return question_id, choices


def answer(client, attempt_id, question_id, choice_id):
    return client.post(
        f"/student/quiz/{QUIZ_ID}/take",
        data={
            "attempt_id": attempt_id,
            "question_id": question_id,
            "choice_id": choice_id,
            "go": "1",
        },
    )


def submit(client, attempt_id):
    return client.post(
        f"/student/quiz/{QUIZ_ID}/submit",
        data={"attempt_id": attempt_id, "confirm": "yes"},
    )


def events(db_path, attempt_id):
    with get_connection(db_path) as connection:
        return [
            dict(row)
            for row in connection.execute(
                "SELECT action, actor_id, metadata, timestamp FROM attempt_audit "
                "WHERE attempt_id = ? ORDER BY audit_id",
                (attempt_id,),
            )
        ]


def actions(db_path, attempt_id):
    return [event["action"] for event in events(db_path, attempt_id)]


def test_starting_an_attempt_records_one_started_event(client, db_path):
    login(client)
    attempt_id = start(client, db_path)

    log = events(db_path, attempt_id)

    assert [event["action"] for event in log] == ["ATTEMPT_STARTED"]
    assert log[0]["actor_id"] == STUDENT_ID
    assert log[0]["timestamp"] == "2026-10-31T08:00:00"


def test_resuming_an_open_attempt_does_not_record_a_second_start(client, db_path):
    login(client)
    attempt_id = start(client, db_path)

    start(client, db_path)  # student presses "Take quiz" again

    assert actions(db_path, attempt_id) == ["ATTEMPT_STARTED"]


def test_saving_an_answer_records_question_and_choice(client, db_path, clock):
    login(client)
    attempt_id = start(client, db_path)
    question_id, choices = first_question_and_choice(db_path)
    clock["now"] = START + timedelta(minutes=2)

    answer(client, attempt_id, question_id, choices[0])
    answer(client, attempt_id, question_id, choices[1])  # student changes mind

    saved = [e for e in events(db_path, attempt_id) if e["action"] == "ANSWER_SAVED"]
    assert [json.loads(e["metadata"]) for e in saved] == [
        {"question_id": question_id, "choice_id": choices[0]},
        {"question_id": question_id, "choice_id": choices[1]},
    ]
    assert saved[0]["timestamp"] == "2026-10-31T08:02:00"


def test_rejected_answer_is_not_recorded(client, db_path):
    login(client)
    attempt_id = start(client, db_path)
    question_id, _ = first_question_and_choice(db_path)

    response = answer(client, attempt_id, question_id, 999999)  # not a real choice

    assert response.status_code == 400
    assert actions(db_path, attempt_id) == ["ATTEMPT_STARTED"]


def test_submission_records_exactly_one_event_with_the_stored_timestamp(
    client, db_path, clock
):
    login(client)
    attempt_id = start(client, db_path)
    question_id, choices = first_question_and_choice(db_path)
    answer(client, attempt_id, question_id, choices[0])
    clock["now"] = START + timedelta(minutes=5)

    assert submit(client, attempt_id).status_code == 302

    log = events(db_path, attempt_id)
    assert [e["action"] for e in log] == [
        "ATTEMPT_STARTED",
        "ANSWER_SAVED",
        "ATTEMPT_SUBMITTED",
    ]
    assert all(e["actor_id"] == STUDENT_ID for e in log)
    with get_connection(db_path) as connection:
        submitted_at = connection.execute(
            "SELECT submitted_at FROM attempt WHERE attempt_id = ?", (attempt_id,)
        ).fetchone()[0]
    assert log[-1]["timestamp"] == submitted_at == "2026-10-31T08:05:00"


def test_second_submit_request_adds_no_second_submission_event(client, db_path):
    login(client)
    attempt_id = start(client, db_path)
    submit(client, attempt_id)

    again = submit(client, attempt_id)

    assert again.status_code == 409
    assert actions(db_path, attempt_id).count("ATTEMPT_SUBMITTED") == 1


def test_unconfirmed_submit_with_unanswered_questions_is_not_recorded(client, db_path):
    login(client)
    attempt_id = start(client, db_path)

    response = client.post(
        f"/student/quiz/{QUIZ_ID}/submit", data={"attempt_id": attempt_id}
    )

    assert response.status_code == 422
    assert "ATTEMPT_SUBMITTED" not in actions(db_path, attempt_id)


def test_timeout_records_one_auto_submitted_event_at_the_deadline(
    client, db_path, clock
):
    login(client)
    attempt_id = start(client, db_path)
    clock["now"] = START + DURATION + timedelta(minutes=3)  # student comes back late

    first = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")
    second = client.get(f"/student/quiz/{QUIZ_ID}/take?q=1")

    assert first.status_code == 302 and second.status_code in (302, 409)
    log = events(db_path, attempt_id)
    assert [e["action"] for e in log] == ["ATTEMPT_STARTED", "AUTO_SUBMITTED"]
    assert json.loads(log[-1]["metadata"]) == {"reason": "time_expired"}
    # Stamped when time ran out, matching attempt.submitted_at, not when the student returned.
    assert log[-1]["timestamp"] == "2026-10-31T08:20:00"


def test_late_answer_is_not_saved_and_only_auto_submit_is_recorded(
    client, db_path, clock
):
    login(client)
    attempt_id = start(client, db_path)
    question_id, choices = first_question_and_choice(db_path)
    clock["now"] = START + DURATION + timedelta(minutes=1)

    answer(client, attempt_id, question_id, choices[0])

    assert actions(db_path, attempt_id) == ["ATTEMPT_STARTED", "AUTO_SUBMITTED"]


def test_lecturer_and_ta_see_the_recorded_events_on_the_audit_page(client, db_path):
    login(client)
    attempt_id = start(client, db_path)
    question_id, choices = first_question_and_choice(db_path)
    answer(client, attempt_id, question_id, choices[0])
    submit(client, attempt_id)
    url = f"/lecturer/quiz/{QUIZ_ID}/attempts/{attempt_id}/audit"

    for email in ("ngan.lecturer@example.edu", "mai.ta@example.edu"):
        login(client, email)
        page = client.get(url).get_data(as_text=True)
        for action in ("ATTEMPT_STARTED", "ANSWER_SAVED", "ATTEMPT_SUBMITTED"):
            assert action in page


def test_audit_history_cannot_be_rewritten_after_submission(client, db_path):
    login(client)
    attempt_id = start(client, db_path)
    submit(client, attempt_id)
    before = events(db_path, attempt_id)

    with get_connection(db_path) as connection:
        with pytest.raises(Exception, match="IMMUTABLE_RECORD"):
            connection.execute(
                "UPDATE attempt_audit SET action = 'ATTEMPT_STARTED' WHERE attempt_id = ?",
                (attempt_id,),
            )

    assert events(db_path, attempt_id) == before
