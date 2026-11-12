"""Issue #156: public readiness and privacy-preserving operational logs."""
import json
import sqlite3

import pytest
from flask import abort

from src.app import create_app


@pytest.fixture
def health_app(tmp_path):
    return create_app({"TESTING": True, "DATABASE_PATH": tmp_path / "health.db"})


def test_health_is_available_to_guest(health_app):
    client = health_app.test_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok", "database": "ok"}
    assert "Location" not in response.headers
    with client.session_transaction() as session:
        assert "user_id" not in session


@pytest.mark.parametrize("failure", ["missing", "missing_table", "corrupt", "connection"])
def test_health_database_failure_is_safe(health_app, failure, monkeypatch, capsys):
    path = health_app.config["DATABASE_PATH"]
    if failure == "missing":
        path = path.parent / "missing.db"
        health_app.config["DATABASE_PATH"] = path
    elif failure == "missing_table":
        with sqlite3.connect(path) as connection:
            connection.execute('DROP TABLE "user"')
    elif failure == "corrupt":
        path.write_bytes(b"not a database")
    else:
        def unavailable(*args, **kwargs):
            raise sqlite3.OperationalError("private-password private@example.com")
        monkeypatch.setattr("src.app.sqlite3.connect", unavailable)

    response = health_app.test_client().get("/health")
    assert response.status_code == 503
    assert response.json == {"status": "error", "database": "unavailable"}
    captured = capsys.readouterr()
    assert "private" not in captured.out + captured.err + response.get_data(as_text=True)
    records = [json.loads(line) for line in captured.out.splitlines()]
    assert records[0]["event"] == "server_exception"
    assert records[0]["status_code"] == 503
    assert records[0]["stack_trace"]
    if failure == "missing":
        assert not path.exists()
    elif failure == "missing_table":
        with sqlite3.connect(path) as connection:
            assert connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name = 'user'"
            ).fetchone() is None


def test_health_accepts_empty_user_table(health_app):
    with sqlite3.connect(health_app.config["DATABASE_PATH"]) as connection:
        connection.execute('CREATE TABLE empty_user (user_id INTEGER)')
        connection.execute('DROP TABLE "user"')
        connection.execute('ALTER TABLE empty_user RENAME TO "user"')
    assert health_app.test_client().get("/health").status_code == 200


def test_request_log_fields_and_duration(health_app, monkeypatch, capsys):
    ticks = iter([10.0, 10.125])
    monkeypatch.setattr("src.app.perf_counter", lambda: next(ticks))
    health_app.test_client().get("/health")
    record = json.loads(capsys.readouterr().out)
    assert record == {
        "event": "http_request", "method": "GET", "path": "/health",
        "status_code": 200, "duration_ms": 125.0,
    }


@pytest.mark.parametrize("body_type", ["form", "json"])
def test_sensitive_request_data_and_exceptions_are_not_logged(health_app, capsys, body_type):
    secrets = {
        "password": "private-password", "email": "private@example.com",
        "session_token": "private-token", "answer": "private-quiz-answer",
    }

    @health_app.post("/explode/<value>")
    def explode(value):
        try:
            raise ValueError("private-password private@example.com private-quiz-answer")
        except ValueError as cause:
            error = RuntimeError(" ".join(secrets.values()))
            error.add_note("private-token")
            raise error from cause

    client = health_app.test_client()
    client.set_cookie("session", secrets["session_token"])
    kwargs = {"json" if body_type == "json" else "data": secrets}
    response = client.post(
        "/explode/private@example.com", query_string=secrets,
        headers={"Authorization": "Bearer private-token"}, **kwargs,
    )
    assert response.status_code == 500
    # Also cover arbitrary unmatched URLs, which can contain sensitive values.
    assert client.get("/private-quiz-answer").status_code == 404
    captured = capsys.readouterr()
    for secret in secrets.values():
        assert secret not in captured.out + captured.err + response.get_data(as_text=True)
    records = [json.loads(line) for line in captured.out.splitlines()]
    assert records[0]["event"] == "server_exception"
    assert records[0]["status_code"] == 500
    frames = records[0]["stack_trace"]
    assert frames
    assert frames[-1]["file"] == "tests/test_health_logging.py"
    assert frames[-1]["function"] == "explode"
    assert all(set(frame) == {"file", "function", "line"} for frame in frames)
    assert all(isinstance(frame["line"], int) and frame["line"] > 0 for frame in frames)
    assert records[1]["path"] == "/explode/<value>"
    assert records[1]["method"] == "POST"
    assert records[1]["status_code"] == 500
    assert records[1]["duration_ms"] >= 0
    assert records[2]["path"] == "<unmatched>"
    assert not captured.err


def test_wrong_password_login_does_not_leak_credentials(health_app, capsys, caplog):
    email = "duc.student@example.edu"
    password = "private-wrong-login-password"
    client = health_app.test_client()
    response = client.post("/login", data={"email": email, "password": password})

    assert response.status_code == 401
    assert "Incorrect email or password." in response.get_data(as_text=True)
    with client.session_transaction() as session:
        assert "user_id" not in session
    # Confirm the real authentication flow recorded a failed attempt.
    with sqlite3.connect(health_app.config["DATABASE_PATH"]) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM user WHERE email = ?", (email,)
        ).fetchone()[0] == 1
        assert connection.execute(
            "SELECT COUNT(*) FROM login_failure WHERE email = ?", (email,)
        ).fetchone()[0] == 1
    captured = capsys.readouterr()
    logs = captured.out + captured.err + caplog.text
    assert password not in logs
    assert email not in logs
    record = json.loads(captured.out)
    assert record["event"] == "http_request"
    assert record["method"] == "POST"
    assert record["path"] == "/login"
    assert record["status_code"] == 401


def test_http_server_error_logs_filtered_stack_trace(health_app, capsys):
    @health_app.get("/unavailable")
    def unavailable():
        abort(503, description="private-password private@example.com")

    response = health_app.test_client().get("/unavailable")
    assert response.status_code == 503
    captured = capsys.readouterr()
    assert "private" not in captured.out + captured.err + response.get_data(as_text=True)
    records = [json.loads(line) for line in captured.out.splitlines()]
    assert records[0]["status_code"] == 503
    assert any(frame["function"] == "unavailable" for frame in records[0]["stack_trace"])
    assert records[1]["status_code"] == 503


def test_http_errors_keep_their_status_without_exception_log(health_app, capsys):
    @health_app.get("/forbidden")
    def forbidden():
        abort(403)

    assert health_app.test_client().get("/forbidden").status_code == 403
    record = json.loads(capsys.readouterr().out)
    assert record["event"] == "http_request"
    assert record["status_code"] == 403
