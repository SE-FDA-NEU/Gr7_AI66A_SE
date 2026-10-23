"""SQLite connection helpers."""

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


def ensure_quiz_duration_unlimited_column(connection: sqlite3.Connection) -> None:
    """Add the unlimited-duration setting to databases created by older versions."""
    quiz_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'quiz'"
    ).fetchone()
    if quiz_table is None:
        return

    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(quiz)")
    }
    if "duration_unlimited" not in columns:
        connection.execute(
            """
            ALTER TABLE quiz
            ADD COLUMN duration_unlimited INTEGER NOT NULL DEFAULT 0
                CHECK (duration_unlimited IN (0, 1))
            """
        )
        connection.commit()
