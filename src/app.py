from __future__ import annotations
import os
import secrets
import sys
from pathlib import Path

from dotenv import load_dotenv

from flask import Flask, redirect, url_for
from werkzeug.exceptions import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from src.errors import render_error
from src.db import ensure_quiz_schema_columns, get_connection
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

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        return render_error(error.code or 500)

    @app.route('/')
    def index():
        return redirect(url_for("auth.login"))

    @app.route('/health')
    def health():
        return {"status": "ok"}

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)