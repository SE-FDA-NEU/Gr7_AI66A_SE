"""Tests for ensure_database(): seed a missing database, never wipe an existing one (#155)."""
from __future__ import annotations
import sqlite3

from src.init_db import ensure_database


def _query_one(db_path, sql, params=()):
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute(sql, params).fetchone()
    finally:
        connection.close()


def test_ED01_missing_database_is_created_and_seeded(tmp_path):
    # ED01: no file yet -> ensure_database creates the schema and loads the 7 seed users.
    db_path = tmp_path / "minilms.db"
    assert not db_path.exists()

    ensure_database(db_path)

    table = _query_one(
        db_path,
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'user'",
    )
    assert table is not None
    assert _query_one(db_path, "SELECT COUNT(*) FROM user")[0] == 7


def test_ED02_existing_database_is_not_reseeded(tmp_path):
    # ED02: a lecturer's edit must survive a restart, so a second call must not run init_db.
    db_path = tmp_path / "minilms.db"
    ensure_database(db_path)

    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            "UPDATE quiz SET title = ? WHERE quiz_id = 1", ("Edited by lecturer",)
        )
        connection.commit()
    finally:
        connection.close()

    ensure_database(db_path)

    title = _query_one(db_path, "SELECT title FROM quiz WHERE quiz_id = 1")[0]
    assert title == "Edited by lecturer"


def test_ED03_missing_nested_parent_directories_are_created(tmp_path):
    # ED03: a fresh server may lack the whole data folder tree; it must be created.
    db_path = tmp_path / "a" / "b" / "c" / "minilms.db"
    assert not db_path.parent.exists()

    ensure_database(db_path)

    assert db_path.is_file()
