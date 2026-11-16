"""Login lockout is keyed by (email, client), so strangers cannot lock a victim.

LK-01 .. LK-10.
"""
from __future__ import annotations

import sqlite3

import pytest
from flask import request

import src.auth as auth_module
from src.app import create_app
from src.client_identity import client_key
from src.db import get_connection
from src.init_db import init_db

PASSWORD = "MiniLMS2026!"
VICTIM = "duc.student@example.edu"
OTHER = "lan.student@example.edu"
ATTACKER_IP = "203.0.113.10"
VICTIM_IP = "198.51.100.20"
NOW = 1_800_000_000


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "lock.db"
    init_db(path)
    return path


def make_app(db_path, **extra):
    config = {
        "TESTING": True,
        "DATABASE_PATH": str(db_path),
        "SECRET_KEY": "test-only-secret",
    }
    config.update(extra)
    return create_app(config)


@pytest.fixture
def client(db_path, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: NOW)
    return make_app(db_path).test_client()


def sign_in(client, email, password=PASSWORD, ip=VICTIM_IP):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        environ_overrides={"REMOTE_ADDR": ip},
    )


def test_lk01_attacker_cannot_lock_the_real_owner(client):
    # The reported bug: 5 wrong passwords from a stranger used to cause 429
    # for everyone.
    for _ in range(5):
        response = sign_in(client, VICTIM, "wrong", ip=ATTACKER_IP)
    assert response.status_code == 429

    response = sign_in(client, VICTIM, PASSWORD, ip=VICTIM_IP)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/student/dashboard")


def test_lk02_locked_client_stays_blocked_even_with_correct_password(client):
    for _ in range(5):
        sign_in(client, VICTIM, "wrong", ip=ATTACKER_IP)

    assert sign_in(client, VICTIM, PASSWORD, ip=ATTACKER_IP).status_code == 429


def test_lk03_failures_from_different_clients_are_counted_separately(client):
    for ip in (ATTACKER_IP, VICTIM_IP):
        for _ in range(4):
            assert sign_in(client, VICTIM, "wrong", ip=ip).status_code == 401
    # 8 failures in total, but never 5 from one client: nobody is locked.
    assert sign_in(client, VICTIM, PASSWORD, ip=VICTIM_IP).status_code == 302


def test_lk04_one_client_trying_many_accounts_gets_blocked(db_path, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: NOW)
    client = make_app(db_path, LOGIN_CLIENT_FAILURE_LIMIT=6).test_client()
    for i in range(5):  # 1 failure per account: pair limit never reached
        assert sign_in(client, f"nobody{i}@example.edu", "x", ip=ATTACKER_IP).status_code == 401
    assert sign_in(client, "nobody5@example.edu", "x", ip=ATTACKER_IP).status_code == 429
    # Even a valid login from that client is refused, others are unaffected.
    assert sign_in(client, VICTIM, PASSWORD, ip=ATTACKER_IP).status_code == 429
    assert sign_in(client, VICTIM, PASSWORD, ip=VICTIM_IP).status_code == 302


def test_lk05_successful_login_does_not_reset_the_client_counter(db_path, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: NOW)
    client = make_app(db_path, LOGIN_CLIENT_FAILURE_LIMIT=6).test_client()
    for i in range(3):
        sign_in(client, f"nobody{i}@example.edu", "x", ip=ATTACKER_IP)
    assert sign_in(client, OTHER, PASSWORD, ip=ATTACKER_IP).status_code == 302
    client.post("/logout", environ_overrides={"REMOTE_ADDR": ATTACKER_IP})
    for i in range(2):
        assert sign_in(client, f"nobody{i + 3}@example.edu", "x", ip=ATTACKER_IP).status_code == 401
    assert sign_in(client, "nobody5@example.edu", "x", ip=ATTACKER_IP).status_code == 429


def test_lk06_successful_login_clears_that_clients_account_failures(client):
    for _ in range(4):
        sign_in(client, VICTIM, "wrong", ip=VICTIM_IP)
    assert sign_in(client, VICTIM, PASSWORD, ip=VICTIM_IP).status_code == 302
    client.post("/logout", environ_overrides={"REMOTE_ADDR": VICTIM_IP})
    for _ in range(4):  # counter restarted: 4 more are still below 5
        assert sign_in(client, VICTIM, "wrong", ip=VICTIM_IP).status_code == 401


def test_lk07_database_never_stores_the_raw_ip(client, db_path):
    for _ in range(5):
        sign_in(client, VICTIM, "wrong", ip=ATTACKER_IP)
    with get_connection(db_path) as connection:
        keys = [r[0] for r in connection.execute("SELECT client_key FROM login_failure")]
        keys += [r[0] for r in connection.execute("SELECT client_key FROM login_lockout")]
    assert keys and all(len(k) == 32 and ATTACKER_IP not in k for k in keys)
    assert set(keys) == {client_key(ATTACKER_IP, "test-only-secret")}


def test_lk08_client_key_rules():
    secret = "s"
    assert client_key("2001:db8:1:2::1", secret) == client_key("2001:db8:1:2:ffff::9", secret)
    assert client_key("2001:db8:1:2::1", secret) != client_key("2001:db8:1:3::1", secret)
    assert client_key("::ffff:203.0.113.10", secret) == client_key("203.0.113.10", secret)
    assert client_key("203.0.113.10", secret) != client_key("203.0.113.10", "other")
    assert client_key(None, secret) == client_key("not-an-ip", secret)


def _ip_app(db_path, **extra):
    app = make_app(db_path, **extra)
    app.add_url_rule("/_ip", "ip_probe", lambda: request.remote_addr)
    return app


def test_lk09_forged_forwarded_for_is_ignored(db_path):
    headers = {"X-Forwarded-For": "6.6.6.6, 1.2.3.4, 9.9.9.9"}  # 6.6.6.6 forged
    trusted = _ip_app(db_path, TRUSTED_PROXY_COUNT=2).test_client()
    assert trusted.get("/_ip", headers=headers).get_data(as_text=True) == "1.2.3.4"
    untrusted = _ip_app(db_path, TRUSTED_PROXY_COUNT=0).test_client()
    assert untrusted.get("/_ip", headers=headers).get_data(as_text=True) == "127.0.0.1"


def test_lk10_old_database_is_upgraded_in_place(tmp_path, monkeypatch):
    monkeypatch.setattr(auth_module.time, "time", lambda: NOW)
    path = tmp_path / "old.db"
    init_db(path)
    with sqlite3.connect(path) as connection:  # recreate the pre-fix tables
        connection.executescript(
            """
            DROP TABLE client_lockout; DROP TABLE login_lockout; DROP TABLE login_failure;
            CREATE TABLE login_failure (failure_id INTEGER PRIMARY KEY,
                email TEXT NOT NULL, failed_at INTEGER NOT NULL);
            CREATE INDEX login_failure_email_failed_at ON login_failure(email, failed_at);
            CREATE TABLE login_lockout (email TEXT PRIMARY KEY, locked_until INTEGER NOT NULL);
            INSERT INTO login_failure (email, failed_at) VALUES ('duc.student@example.edu', 1);
            """
        )
    client = make_app(path).test_client()
    for _ in range(5):
        response = sign_in(client, VICTIM, "wrong", ip=ATTACKER_IP)
    assert response.status_code == 429
    assert sign_in(client, VICTIM, PASSWORD, ip=VICTIM_IP).status_code == 302
