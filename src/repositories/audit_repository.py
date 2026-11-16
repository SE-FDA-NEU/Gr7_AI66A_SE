"""Ghi và đọc nhật ký audit append-only của các lượt làm bài (US12)."""
from __future__ import annotations

import json
import sqlite3
from typing import Any

from src.time_utils import TIMESTAMP_FORMAT, utc_now_naive


def record_audit_event(
    connection: sqlite3.Connection,
    attempt_id: int,
    actor_id: int,
    action: str,
    metadata: dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> int:
    """Append a new audit record to the history log.

    `timestamp` lets the caller reuse the time it already stored on the attempt
    (e.g. submitted_at), so the audit row and the attempt agree exactly.
    """
    # Nếu caller đã có timestamp nghiệp vụ thì dùng chính timestamp đó để đồng bộ.
    now_str = timestamp or utc_now_naive().strftime(TIMESTAMP_FORMAT)
    metadata_json = json.dumps(metadata) if metadata else None

    # Chỉ INSERT; schema có trigger ngăn sửa/xóa bản ghi sau khi đã ghi.
    cursor = connection.execute(
        """
        INSERT INTO attempt_audit (attempt_id, actor_id, action, metadata, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (attempt_id, actor_id, action, metadata_json, now_str),
    )
    return cursor.lastrowid


def get_attempt_audit_history(
    connection: sqlite3.Connection,
    attempt_id: int,
    lecturer_id: int,
    role: str = "lecturer"
):
    """
    Retrieve chronological audit logs for an attempt.
    Enforces lecturer ownership over the quiz.
    Returns (logs, error_code).
    """
    # Tìm quiz chủ quản để xác minh quyền trước khi đọc log.
    attempt = connection.execute(
        """
        SELECT a.attempt_id, q.quiz_id, q.lecturer_id
        FROM attempt a
        JOIN quiz q ON a.quiz_id = q.quiz_id
        WHERE a.attempt_id = ?
        """,
        (attempt_id,),
    ).fetchone()

    if not attempt:
        return None, "ATTEMPT_NOT_FOUND"

    # TA được xem theo vai trò; giảng viên chỉ xem quiz của mình.
    if role != "ta" and attempt["lecturer_id"] != lecturer_id:
        return None, "NOT_QUIZ_OWNER"

    # Sắp xếp timestamp và audit_id để thứ tự ổn định nếu thời gian trùng nhau.
    logs = connection.execute(
        """
        SELECT 
            au.audit_id,
            au.attempt_id,
            au.actor_id,
            u.name AS actor_name,
            u.role AS actor_role,
            au.action,
            au.metadata,
            au.timestamp
        FROM attempt_audit au
        JOIN user u ON au.actor_id = u.user_id
        WHERE au.attempt_id = ?
        ORDER BY au.timestamp ASC, au.audit_id ASC
        """,
        (attempt_id,),
    ).fetchall()

    return logs, None