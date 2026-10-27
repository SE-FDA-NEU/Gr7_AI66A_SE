"""Database access for authentication and login lockouts."""
from __future__ import annotations
import sqlite3


def get_user_by_email(
    connection: sqlite3.Connection,
    email: str,
) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT user_id, name, email, password_hash, role FROM user WHERE email = ?",
        (email,),
    ).fetchone()


def get_active_lockout(
    connection: sqlite3.Connection,
    email: str,
    now: int,
) -> int | None:
    row = connection.execute(
        "SELECT locked_until FROM login_lockout WHERE email = ?",
        (email,),
    ).fetchone()
    if row is None:
        return None

    locked_until = row["locked_until"]
    if locked_until > now:
        return locked_until

    connection.execute("DELETE FROM login_lockout WHERE email = ?", (email,))
    return None


def record_login_failure(
    connection: sqlite3.Connection,
    email: str,
    now: int,
) -> int | None:
    window_start = now - 10 * 60
    connection.execute(
        "DELETE FROM login_failure WHERE email = ? AND failed_at <= ?",
        (email, window_start),
    )
    connection.execute(
        "INSERT INTO login_failure (email, failed_at) VALUES (?, ?)",
        (email, now),
    )
    failures = connection.execute(
        "SELECT COUNT(*) FROM login_failure WHERE email = ? AND failed_at > ?",
        (email, window_start),
    ).fetchone()[0]

    if failures < 5:
        return None

    locked_until = now + 15 * 60
    connection.execute(
        """
        INSERT INTO login_lockout (email, locked_until)
        VALUES (?, ?)
        ON CONFLICT(email) DO UPDATE SET locked_until = excluded.locked_until
        """,
        (email, locked_until),
    )
    return locked_until


def clear_login_failures(connection: sqlite3.Connection, email: str) -> None:
    connection.execute("DELETE FROM login_failure WHERE email = ?", (email,))
    connection.execute("DELETE FROM login_lockout WHERE email = ?", (email,))
