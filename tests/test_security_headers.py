"""Cookie flags and HTTP security headers (SEC-01 .. SEC-09)."""
from __future__ import annotations

import re

import pytest

from src.app import create_app
from src.init_db import init_db

PASSWORD = "MiniLMS2026!"
STUDENT = "duc.student@example.edu"


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "sec.db"
    init_db(path)
    return path


def make_app(db_path, **extra):
    cfg = {"TESTING": True, "DATABASE_PATH": str(db_path)}
    cfg.update(extra)
    return create_app(cfg)


def login_cookie_header(client):
    response = client.post(
        "/login", data={"email": STUDENT, "password": PASSWORD}
    )
    assert response.status_code == 302
    return response.headers.getlist("Set-Cookie")


def test_sec01_login_page_has_baseline_headers(db_path):
    r = make_app(db_path).test_client().get("/login")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in r.headers["Permissions-Policy"]
    assert r.headers["Cache-Control"] == "no-store"


def test_sec02_csp_blocks_framing_plugins_and_foreign_scripts(db_path):
    csp = make_app(db_path).test_client().get("/login").headers[
        "Content-Security-Policy"
    ]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert "form-action 'self'" in csp
    script_src = re.search(r"script-src ([^;]+)", csp).group(1)
    assert "'unsafe-inline'" not in script_src
    assert "http" not in script_src


def test_sec03_csp_nonce_differs_per_request_and_matches_page(db_path):
    client = make_app(db_path).test_client()
    nonces = []
    login_cookie_header(client)
    for _ in range(2):
        r = client.get("/student/dashboard")
        assert r.status_code == 200
        nonce = re.search(r"'nonce-([^']+)'", r.headers[
            "Content-Security-Policy"]).group(1)
        # every inline <script> carries the nonce of this response
        for tag in re.findall(r"<script(?![^>]*\bsrc=)[^>]*>", r.get_data(as_text=True)):
            assert f'nonce="{nonce}"' in tag
        nonces.append(nonce)
    assert nonces[0] != nonces[1]


def test_sec04_session_cookie_is_httponly_samesite_not_secure_in_tests(db_path):
    cookies = login_cookie_header(make_app(db_path).test_client())
    session = next(c for c in cookies if c.startswith("session="))
    assert "HttpOnly" in session
    assert "SameSite=Lax" in session
    assert "Secure" not in session  # tests run over http


def test_sec05_session_cookie_secure_in_production_mode(db_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.delenv("SESSION_COOKIE_SECURE", raising=False)
    app = create_app({"DATABASE_PATH": str(db_path)})  # not testing, not debug
    assert app.config["SESSION_COOKIE_SECURE"] is True
    client = app.test_client()
    page = client.get("/login", base_url="https://localhost")
    assert "max-age=31536000" in page.headers["Strict-Transport-Security"]
    cookies = page.headers.getlist("Set-Cookie")
    assert all("Secure" in c for c in cookies if c.startswith("session="))


def test_sec06_no_hsts_over_local_development(db_path):
    r = make_app(db_path).test_client().get("/login")
    assert "Strict-Transport-Security" not in r.headers


def test_sec07_env_can_override_secure_flag(db_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "0")
    app = create_app({"DATABASE_PATH": str(db_path)})
    assert app.config["SESSION_COOKIE_SECURE"] is False


def test_sec08_invalid_env_value_is_rejected(db_path, monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "maybe")
    with pytest.raises(RuntimeError):
        create_app({"DATABASE_PATH": str(db_path)})


def test_sec09_static_files_are_cacheable_but_still_get_nosniff(db_path):
    r = make_app(db_path).test_client().get("/static/js/ui.js")
    assert r.status_code == 200
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers.get("Cache-Control") != "no-store"
