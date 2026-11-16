"""Cookie and HTTP security-header configuration.

Kept in one module so the policy is easy to review and to test.
"""
from __future__ import annotations

import os
import secrets
from datetime import timedelta

from flask import Flask, g, request

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off"}

# One year. Browsers ignore HSTS sent over plain http, so it is safe to send
# whenever the app is configured for https (Secure cookies).
HSTS_VALUE = "max-age=31536000; includeSubDomains"

PERMISSIONS_POLICY = (
    "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
)


def _env_flag(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    value = raw.strip().lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise RuntimeError(f"{name} must be one of 1/0/true/false, got {raw!r}.")


def configure_cookies(app: Flask, test_config: dict | None = None) -> None:
    """Set cookie flags. Call after test_config has been applied.

    SESSION_COOKIE_SECURE is ON by default and turned off only for local
    development (debug) and automated tests, which run over plain http.
    It can be forced either way with the SESSION_COOKIE_SECURE env variable
    (e.g. set it to 0 when running gunicorn on http://127.0.0.1 in Safari).
    """
    # Flask's own default for this key is False, so "already in app.config"
    # cannot tell whether someone chose it: only an explicit test_config can.
    if not test_config or "SESSION_COOKIE_SECURE" not in test_config:
        forced = _env_flag("SESSION_COOKIE_SECURE")
        app.config["SESSION_COOKIE_SECURE"] = (
            forced if forced is not None else not (app.debug or app.testing)
        )
    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    # Session cookie is a browser-session cookie; also cap the server-side
    # lifetime in case a session is ever marked permanent.
    app.config.setdefault("PERMANENT_SESSION_LIFETIME", timedelta(hours=8))


def build_csp(nonce: str) -> str:
    # Scripts: only same-origin files and inline <script nonce="...">.
    # Styles: templates still use inline <style> blocks and style="..."
    # attributes, so 'unsafe-inline' is kept for styles only (low risk
    # compared with scripts). Remove it once styles move to static/css.
    return "; ".join([
        "default-src 'self'",
        f"script-src 'self' 'nonce-{nonce}'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    ])


def init_security_headers(app: Flask) -> None:
    @app.before_request
    def make_csp_nonce():
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject_csp_nonce():
        return {"csp_nonce": g.get("csp_nonce", "")}

    @app.after_request
    def set_security_headers(response):
        headers = response.headers
        nonce = g.get("csp_nonce") or secrets.token_urlsafe(16)
        headers.setdefault("Content-Security-Policy", build_csp(nonce))
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        if app.config.get("SESSION_COOKIE_SECURE"):
            headers.setdefault("Strict-Transport-Security", HSTS_VALUE)
        # Pages hold grades, answers and login state: do not let browsers or
        # proxies cache them. Static assets may be cached.
        if request.endpoint != "static":
            headers.setdefault("Cache-Control", "no-store")
        return response
