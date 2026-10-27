from __future__ import annotations

import sqlite3
import pytest

from src.app import create_app
from src.db import get_connection
from src.init_db import init_db
from src.repositories.audit_repository import (
    get_attempt_audit_history,
    record_audit_event,
)


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "minilms_test.db"
    init_db(path)
    
    # Chèn trước 1 lượt làm bài mẫu (attempt_id = 1)
    with get_connection(path) as conn:
        conn.execute(
            """
            INSERT INTO attempt (attempt_id, student_id, quiz_id, started_at)
            VALUES (1, 3, 1, '2026-10-27T08:00:00')
            """
        )
        conn.commit()
    return path


@pytest.fixture
def client(db_path):
    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    return app.test_client()


def login(client, email="ngan.lecturer@example.edu"):
    client.post("/logout")  # Clear session cu trước khi login mới
    return client.post("/login", data={"email": email, "password": "MiniLMS2026!"})


def test_us12_record_and_retrieve_audit_history_chronologically(db_path):
    """UT-US12-01: Ghi vết các sự kiện và kiểm tra danh sách sắp xếp theo thời gian."""
    with get_connection(db_path) as conn:
        record_audit_event(conn, attempt_id=1, actor_id=3, action="ATTEMPT_STARTED")
        record_audit_event(
            conn,
            attempt_id=1,
            actor_id=3,
            action="ANSWER_SAVED",
            metadata={"question_id": 1, "choice_id": 2},
        )
        record_audit_event(conn, attempt_id=1, actor_id=3, action="ATTEMPT_SUBMITTED")
        conn.commit()

        # Ngan (lecturer_id=1) sở hữu Quiz 1
        logs, error = get_attempt_audit_history(conn, attempt_id=1, lecturer_id=1)

    assert error is None
    assert len(logs) == 3
    assert logs[0]["action"] == "ATTEMPT_STARTED"
    assert logs[1]["action"] == "ANSWER_SAVED"
    assert logs[2]["action"] == "ATTEMPT_SUBMITTED"


def test_us12_unauthorized_lecturer_cannot_view_audit_history(db_path):
    """UT-US12-02: Giảng viên không sở hữu Quiz không thể xem audit log."""
    with get_connection(db_path) as conn:
        record_audit_event(conn, attempt_id=1, actor_id=3, action="ATTEMPT_STARTED")
        conn.commit()

        # Nam (lecturer_id=2) không sở hữu Quiz 1
        logs, error = get_attempt_audit_history(conn, attempt_id=1, lecturer_id=2)

    assert logs is None
    assert error == "NOT_QUIZ_OWNER"


def test_us12_non_existent_attempt_returns_404_error(db_path):
    """UT-US12-03: Lượt làm bài không tồn tại trả về ATTEMPT_NOT_FOUND."""
    with get_connection(db_path) as conn:
        logs, error = get_attempt_audit_history(conn, attempt_id=9999, lecturer_id=1)

    assert logs is None
    assert error == "ATTEMPT_NOT_FOUND"


def test_us12_immutability_db_trigger_prevents_update(db_path):
    """UT-US12-04: SQLite trigger ngăn chặn mọi câu lệnh UPDATE trên bảng attempt_audit."""
    with get_connection(db_path) as conn:
        log_id = record_audit_event(conn, attempt_id=1, actor_id=3, action="ATTEMPT_STARTED")
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            conn.execute(
                "UPDATE attempt_audit SET action = 'TAMPERED' WHERE audit_id = ?",
                (log_id,),
            )

        assert "IMMUTABLE_RECORD" in str(exc_info.value)


def test_us12_immutability_db_trigger_prevents_delete(db_path):
    """UT-US12-05: SQLite trigger ngăn chặn mọi câu lệnh DELETE trên bảng attempt_audit."""
    with get_connection(db_path) as conn:
        log_id = record_audit_event(conn, attempt_id=1, actor_id=3, action="ATTEMPT_STARTED")
        conn.commit()

        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            conn.execute(
                "DELETE FROM attempt_audit WHERE audit_id = ?",
                (log_id,),
            )

        assert "IMMUTABLE_RECORD" in str(exc_info.value)


def test_us12_route_lecturer_audit_view_access_control(client, db_path):
    """UT-US12-06: Kiểm tra quyền truy cập Route người dùng từ xa."""
    # 1. Chưa đăng nhập -> Chuyển hướng /login
    response = client.get("/lecturer/quiz/1/attempts/1/audit")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")

    # 2. Đăng nhập tư cách Học sinh -> 403 Forbidden
    login(client, "duc.student@example.edu")
    response = client.get("/lecturer/quiz/1/attempts/1/audit")
    assert response.status_code == 403

    # 3. Đăng nhập tư cách Giảng viên sở hữu Quiz -> 200 OK
    login(client, "ngan.lecturer@example.edu")
    with get_connection(db_path) as conn:
        record_audit_event(conn, attempt_id=1, actor_id=3, action="ATTEMPT_STARTED")
        conn.commit()

    response = client.get("/lecturer/quiz/1/attempts/1/audit")
    assert response.status_code == 200