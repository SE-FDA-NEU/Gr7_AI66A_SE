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
