"""SQLite connection helpers."""
from __future__ import annotations
import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open a database connection with foreign keys and named row access enabled."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_quiz_schema_columns(connection: sqlite3.Connection) -> None:
    """Add quiz settings introduced after the initial database schema."""
    quiz_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'quiz'"
    ).fetchone()
    if quiz_table is None:
        return

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
    for name, definition in additions.items():
        if name not in columns:
            connection.execute(f"ALTER TABLE quiz ADD COLUMN {name} {definition}")

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
    def columns(table: str) -> set[str]:
        return {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}

    failure_columns = columns("login_failure")
    if not failure_columns:
        return  # fresh database: init_db() creates everything

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
