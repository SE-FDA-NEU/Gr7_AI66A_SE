"""Database access for authentication and login lockouts.

Lockouts are keyed by (email, client_key) so that failed attempts from one
visitor never block the real owner of the account on another network. A
second, larger limit per client_key stops one visitor from trying many
different accounts.
"""
from __future__ import annotations
import sqlite3

WINDOW_SECONDS = 10 * 60
LOCKOUT_SECONDS = 15 * 60
ACCOUNT_FAILURE_LIMIT = 5      # same email from the same client, per window
DEFAULT_CLIENT_FAILURE_LIMIT = 50  # any email from the same client, per window


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
    client_key: str = "",
) -> int | None:
    """Return locked_until if this client is locked out of this account, or
    out of the whole login form, otherwise None. Expired rows are removed."""
    until = None
    row = connection.execute(
        "SELECT locked_until FROM login_lockout WHERE email = ? AND client_key = ?",
        (email, client_key),
    ).fetchone()
    if row is not None:
        if row["locked_until"] > now:
            until = row["locked_until"]
        else:
            connection.execute(
                "DELETE FROM login_lockout WHERE email = ? AND client_key = ?",
                (email, client_key),
            )

    row = connection.execute(
        "SELECT locked_until FROM client_lockout WHERE client_key = ?",
        (client_key,),
    ).fetchone()
    if row is not None:
        if row["locked_until"] > now:
            until = max(until or 0, row["locked_until"])
        else:
            connection.execute(
                "DELETE FROM client_lockout WHERE client_key = ?", (client_key,)
            )
    return until


def record_login_failure(
    connection: sqlite3.Connection,
    email: str,
    now: int,
    client_key: str = "",
    client_limit: int = DEFAULT_CLIENT_FAILURE_LIMIT,
) -> int | None:
    """Store one failed attempt. Return locked_until if it caused a lockout."""
    window_start = now - WINDOW_SECONDS
    connection.execute("DELETE FROM login_failure WHERE failed_at <= ?", (window_start,))
    connection.execute(
        "INSERT INTO login_failure (email, client_key, failed_at) VALUES (?, ?, ?)",
        (email, client_key, now),
    )
    account_failures = connection.execute(
        "SELECT COUNT(*) FROM login_failure "
        "WHERE email = ? AND client_key = ? AND failed_at > ?",
        (email, client_key, window_start),
    ).fetchone()[0]
    client_failures = connection.execute(
        "SELECT COUNT(*) FROM login_failure WHERE client_key = ? AND failed_at > ?",
        (client_key, window_start),
    ).fetchone()[0]

    locked_until = None
    if account_failures >= ACCOUNT_FAILURE_LIMIT:
        locked_until = now + LOCKOUT_SECONDS
        connection.execute(
            """
            INSERT INTO login_lockout (email, client_key, locked_until)
            VALUES (?, ?, ?)
            ON CONFLICT(email, client_key) DO UPDATE
                SET locked_until = excluded.locked_until
            """,
            (email, client_key, locked_until),
        )
    if client_limit and client_failures >= client_limit:
        locked_until = now + LOCKOUT_SECONDS
        connection.execute(
            """
            INSERT INTO client_lockout (client_key, locked_until)
            VALUES (?, ?)
            ON CONFLICT(client_key) DO UPDATE
                SET locked_until = excluded.locked_until
            """,
            (client_key, locked_until),
        )
    return locked_until


def clear_login_failures(
    connection: sqlite3.Connection,
    email: str,
    client_key: str = "",
) -> None:
    """Forget this client's failures for this account after a good login.

    Deliberately does NOT reset the per-client counter: otherwise an attacker
    could log into their own account between guesses to start over.
    """
    connection.execute(
        "DELETE FROM login_failure WHERE email = ? AND client_key = ?",
        (email, client_key),
    )
    connection.execute(
        "DELETE FROM login_lockout WHERE email = ? AND client_key = ?",
        (email, client_key),
    )
