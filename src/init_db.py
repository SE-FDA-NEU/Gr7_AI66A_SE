"""Create the local database and load its checked-in sample data."""
from __future__ import annotations
import csv
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

try:
    from src.db import get_connection
    from src.schema import SCHEMA_SQL, TABLE_NAMES
except ModuleNotFoundError:
    from db import get_connection
    from schema import SCHEMA_SQL, TABLE_NAMES


ROOT = Path(__file__).resolve().parent.parent

SEED_FILES = {
    "user": "seed_users.csv",
    "quiz": "seed_quizzes.csv",
    "question": "seed_questions.csv",
    "choice": "seed_choices.csv",
}


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """Read a seed CSV file and return its columns and rows."""
    with path.open(newline="", encoding="utf-8-sig") as seed_file:
        reader = csv.DictReader(seed_file)

        if reader.fieldnames is None:
            raise ValueError(f"Seed file has no header: {path}")

        return list(reader.fieldnames), list(reader)


def init_db(db_path: str | Path) -> dict[str, int]:
    """Recreate all tables, seed sample rows, and return per-table counts."""
    db_path = Path(db_path)
    counts: dict[str, int] = {}

    with get_connection(db_path) as connection:
        connection.executescript(SCHEMA_SQL)

        for table, filename in SEED_FILES.items():
            columns, rows = _read_csv(ROOT / "data" / filename)

            column_sql = ", ".join(f'"{column}"' for column in columns)
            placeholders = ", ".join("?" for _ in columns)

            connection.executemany(
                f"INSERT INTO {table} ({column_sql}) VALUES ({placeholders})",
                [[row[column] for column in columns] for row in rows],
            )

            counts[table] = len(rows)

        counts["attempt"] = connection.execute(
            "SELECT COUNT(*) FROM attempt"
        ).fetchone()[0]

        counts["answer"] = connection.execute(
            "SELECT COUNT(*) FROM answer"
        ).fetchone()[0]

    return {table: counts.get(table, 0) for table in TABLE_NAMES}


def _has_user_table(db_path: Path) -> bool:
    """Return True when the database file already contains the user table."""
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'user'"
        ).fetchone() is not None
    finally:
        connection.close()


def ensure_database(db_path: str | Path) -> bool:
    """Create and seed the database only when it is missing.

    An existing database that already has the user table is left untouched,
    because init_db() drops every table first. Returns True when seeding ran.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists() and _has_user_table(db_path):
        return False

    init_db(db_path)
    return True


def _display_path(db_path: Path) -> str:
    """Return a readable database path for terminal output."""
    try:
        return db_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(db_path)


def main() -> None:
    """Initialize the database using DATABASE_PATH from .env when available."""
    load_dotenv(ROOT / ".env")

    configured_path = Path(
        os.getenv("DATABASE_PATH", "data/minilms.db")
    )

    if configured_path.is_absolute():
        db_path = configured_path
    else:
        db_path = ROOT / configured_path

    counts = init_db(db_path)

    print(f"[INFO] Database: {_display_path(db_path)}")
    print(
        f"[INFO] Created 6 tables: {', '.join(TABLE_NAMES)}"
    )
    print(f"[INFO] Seeded user: {counts['user']}")
    print(f"[INFO] Seeded quiz: {counts['quiz']}")
    print(f"[INFO] Seeded question: {counts['question']}")
    print(f"[INFO] Seeded choice: {counts['choice']}")
    print(f"[DONE] {sum(counts.values())} rows in total")


if __name__ == "__main__":
    main()