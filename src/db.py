"""Các hàm dùng chung để kết nối và nâng cấp schema SQLite.

Repository sử dụng get_connection() để có foreign key và truy cập cột theo tên;
các hàm ensure_* giúp ứng dụng nâng cấp DB hiện có khi khởi động.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open a database connection with foreign keys and named row access enabled."""
    # Tạo thư mục cha nếu DB đặt trong thư mục chưa tồn tại.
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    # sqlite3.Row cho phép lấy cột bằng tên, ví dụ row["email"].
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_quiz_schema_columns(connection: sqlite3.Connection) -> None:
    """Add quiz settings introduced after the initial database schema."""
    # DB chưa có bảng quiz thì chưa có gì cần nâng cấp.
    quiz_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'quiz'"
    ).fetchone()
    if quiz_table is None:
        return

    # So sánh cột hiện tại với các cột mới để migration có thể chạy lặp an toàn.
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(quiz)")
    }
    additions = {
        "duration_unlimited": """
            INTEGER NOT NULL DEFAULT 0 CHECK (duration_unlimited IN (0, 1))
        """,
        "max_attempts": "INTEGER NOT NULL DEFAULT 1 CHECK (max_attempts > 0)",
        "last_published_end_at": "TEXT",
        "closed_by_deadline": """
            INTEGER NOT NULL DEFAULT 0 CHECK (closed_by_deadline IN (0, 1))
        """,
    }
    # Thêm từng cột còn thiếu mà không ảnh hưởng dữ liệu của các cột cũ.
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE quiz ADD COLUMN {name} {definition}")

    # Ghi lại deadline cũ để biết quiz đóng do hết hạn có được publish lại không.
    if {"status", "end_at"}.issubset(columns):
        connection.execute(
            """
            UPDATE quiz
            SET last_published_end_at = end_at
            WHERE status = 'published' AND last_published_end_at IS NULL
            """
        )
    connection.execute("DROP INDEX IF EXISTS one_submitted_attempt_per_student_quiz")
    connection.commit()


ensure_quiz_duration_unlimited_column = ensure_quiz_schema_columns


def ensure_login_lockout_schema(connection: sqlite3.Connection) -> None:
    """Upgrade an older database so lockouts are keyed by (email, client).

    login_failure/login_lockout only hold short-lived counters, so rebuilding
    login_lockout is safe: it just lifts any lockout that was active.
    """
    # Hàm nhỏ này dùng PRAGMA để đọc tên cột từ bảng được truyền vào.
    def columns(table: str) -> set[str]:
        return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}

    failure_columns = columns("login_failure")
    if not failure_columns:
        return  # fresh database: init_db() creates everything

    # Các migration tiếp theo bổ sung khóa theo client cho bảng đăng nhập cũ.
    if "client_key" not in failure_columns:
        connection.execute(
            "ALTER TABLE login_failure ADD COLUMN client_key TEXT NOT NULL DEFAULT ''"
        )
    if "client_key" not in columns("login_lockout"):
        connection.execute("DROP TABLE IF EXISTS login_lockout")
        connection.execute(
            """
            CREATE TABLE login_lockout (
                email TEXT NOT NULL,
                client_key TEXT NOT NULL DEFAULT '',
                locked_until INTEGER NOT NULL,
                PRIMARY KEY (email, client_key)
            )
            """
        )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS client_lockout (
            client_key TEXT PRIMARY KEY,
            locked_until INTEGER NOT NULL
        )
        """
    )
    connection.execute("DROP INDEX IF EXISTS login_failure_email_failed_at")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS login_failure_email_failed_at "
        "ON login_failure(email, client_key, failed_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS login_failure_client_failed_at "
        "ON login_failure(client_key, failed_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS login_failure_failed_at "
        "ON login_failure(failed_at)"
    )
    connection.commit()
