from __future__ import annotations
import os
import json
import secrets
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from time import perf_counter
from traceback import walk_tb

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


def log_server_exception(error: Exception, status_code: int = 500):
    # Allow only frame locations. Messages, source lines, locals, exception
    # notes and chained exception text can all contain credentials or answers.
    frames = []
    for frame, lineno in walk_tb(error.__traceback__):
        filename = Path(frame.f_code.co_filename)
        try:
            filename = filename.resolve().relative_to(PROJECT_ROOT).as_posix()
        except ValueError:
            filename = "<external>"
        frames.append({
            "file": filename, "function": frame.f_code.co_name, "line": lineno,
        })
    print(json.dumps({
        "event": "server_exception", "status_code": status_code,
        "stack_trace": frames,
    }), flush=True)


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        DEBUG=False,
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE_PATH=os.environ.get('DATABASE_PATH', 'data/minilms.db'),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    if not app.config["SECRET_KEY"]:
        if app.testing or app.debug:
            app.config["SECRET_KEY"] = secrets.token_hex(32)
        else:
            raise RuntimeError(
                "SECRET_KEY must be set in the environment or .env file "
                "when running outside testing or local debug mode."
            )

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
        if (error.code or 500) >= 500:
            log_server_exception(error, error.code or 500)
        return render_error(error.code or 500)

    @app.errorhandler(Exception)
    def handle_server_error(error):
        log_server_exception(error)
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
        except sqlite3.Error as error:
            log_server_exception(error, 503)
            return {"status": "error", "database": "unavailable"}, 503
        return {"status": "ok", "database": "ok"}

    return app


if __name__ == '__main__':
    app = create_app({"DEBUG": True})
    app.run(debug=True, port=5000)
