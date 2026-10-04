"""Create the local database and load its checked-in sample data."""

import csv
import os
from pathlib import Path

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

    counts = {table: counts.get(table, 0) for table in TABLE_NAMES}
    return counts


def _display_path(db_path: Path) -> str:
    try:
        return db_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(db_path)


def main() -> None:
    configured_path = Path(os.getenv("DATABASE_PATH", "data/minilms.db"))
    db_path = configured_path if configured_path.is_absolute() else ROOT / configured_path
    counts = init_db(db_path)

    print(f"[INFO] Database: {_display_path(db_path)}")
    print(f"[INFO] Created 6 tables: {', '.join(TABLE_NAMES)}")
    for table in TABLE_NAMES[:4]:
        print(f"[INFO] Seeded {table}: {counts[table]}")
    print(f"[DONE] {sum(counts.values())} rows in total")


if __name__ == "__main__":
    main()