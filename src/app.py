from __future__ import annotations
import os
import json
import secrets
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv

from flask import Flask, g, redirect, request, url_for
from werkzeug.exceptions import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.errors import render_error
from src.db import ensure_quiz_schema_columns, get_connection
from src.init_db import ensure_database
from src.routes.api_routes import api_bp
from src.routes.auth_routes import auth_bp
from src.routes.lecturer_routes import lecturer_bp
from src.routes.quiz_routes import quiz_bp
from src.routes.student_routes import student_bp


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE_PATH=os.environ.get('DATABASE_PATH', 'data/minilms.db'),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    database_path = Path(app.config["DATABASE_PATH"])
    ensure_database(database_path)
    if database_path.exists():
        connection = get_connection(database_path)
        try:
            ensure_quiz_schema_columns(connection)
        finally:
            connection.close()

    app.register_blueprint(auth_bp)
    app.register_blueprint(lecturer_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def start_request_timer():
        g.request_started_at = perf_counter()

    @app.after_request
    def log_request(response):
        # Route templates omit user-controlled path values; never log raw URLs,
        # query strings, headers, cookies, bodies, or response content.
        print(json.dumps({
            "event": "http_request",
            "method": request.method if request.method in {
                "GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
            } else "OTHER",
            "path": request.url_rule.rule if request.url_rule else "<unmatched>",
            "status_code": response.status_code,
            "duration_ms": round((perf_counter() - g.request_started_at) * 1000, 3),
        }), flush=True)
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return render_error(error.code or 500)

    @app.errorhandler(Exception)
    def handle_server_error(error):
        # Exception messages and tracebacks may contain credentials or answers.
        print(json.dumps({"event": "server_exception", "status_code": 500}), flush=True)
        return render_error(500)

    @app.route('/')
    def index():
        return redirect(url_for("auth.login"))

    @app.route('/health')
    def health():
        try:
            # Read-only mode must not recreate a lost database or seed tables.
            uri = Path(app.config["DATABASE_PATH"]).resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                connection.execute('SELECT 1 FROM "user" LIMIT 1').fetchone()
        except sqlite3.Error:
            return {"status": "error", "database": "unavailable"}, 503
        return {"status": "ok", "database": "ok"}

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
