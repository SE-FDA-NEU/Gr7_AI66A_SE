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
        raise RuntimeError(" ".join(secrets.values()))

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
    assert records[0] == {"event": "server_exception", "status_code": 500}
    assert records[1]["path"] == "/explode/<value>"
    assert records[1]["method"] == "POST"
    assert records[1]["status_code"] == 500
    assert records[1]["duration_ms"] >= 0
    assert records[2]["path"] == "<unmatched>"
    assert not captured.err


def test_http_errors_keep_their_status_without_exception_log(health_app, capsys):
    @health_app.get("/forbidden")
    def forbidden():
        abort(403)

    assert health_app.test_client().get("/forbidden").status_code == 403
    record = json.loads(capsys.readouterr().out)
    assert record["event"] == "http_request"
    assert record["status_code"] == 403
