"""Điểm khởi chạy ứng dụng MiniLMS và nơi ghép các thành phần Flask.

Luồng tổng quát: tạo cấu hình -> chuẩn bị cơ sở dữ liệu -> đăng ký route,
kiểm tra bảo mật và ghi log -> trả về ứng dụng cho máy chủ web.
"""
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
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.exceptions import HTTPException

# Tính đường dẫn từ vị trí file này để chạy app không phụ thuộc thư mục hiện tại.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Thêm thư mục gốc vào đường dẫn tìm module để các lệnh chạy trực tiếp vẫn import được src.
sys.path.insert(0, str(PROJECT_ROOT))
# Đọc biến cấu hình local từ .env; biến đã có trong môi trường được giữ nguyên.
load_dotenv(PROJECT_ROOT / ".env")

from src.errors import CSRF_FAILED, render_error
from src.client_identity import apply_proxy_fix
from src.db import (
    ensure_login_lockout_schema,
    ensure_quiz_schema_columns,
    get_connection,
)
from src.init_db import ensure_database
from src.routes.api_routes import api_bp
from src.routes.auth_routes import auth_bp
from src.routes.lecturer_routes import lecturer_bp
from src.routes.quiz_routes import quiz_bp
from src.routes.student_routes import student_bp
from src.security import configure_cookies, init_security_headers

csrf = CSRFProtect()


def log_server_exception(error: Exception, status_code: int = 500):
    # Allow only frame locations. Messages, source lines, locals, exception
    # notes and chained exception text can all contain credentials or answers.
    # Chỉ ghi vị trí stack trace, không ghi nội dung lỗi có thể chứa dữ liệu nhạy cảm.
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
    """Tạo Flask app theo mô hình application factory.

    Hàm này được dùng cả khi chạy thật lẫn trong test; test_config cho phép
    thay cơ sở dữ liệu và một số thiết lập mà không sửa cấu hình production.
    """
    app = Flask(__name__)
    # Tin cậy thông tin IP chuyển tiếp chỉ từ số proxy đã được cấu hình.
    apply_proxy_fix(app, test_config)

    # Giá trị mặc định chung; thiết lập test nếu có sẽ ghi đè ở bước tiếp theo.
    app.config.from_mapping(
        DEBUG=False,
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE_PATH=os.environ.get('DATABASE_PATH', 'data/minilms.db'),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # SESSION_COOKIE_SECURE is decided in configure_cookies() below.
        # The default 1-hour token lifetime would reject a student's answer or a
        # lecturer's edit after a long quiz or a long editing session. The token
        # is tied to the session cookie instead, which ends with the browser.
        WTF_CSRF_TIME_LIMIT=None,
    )

    if test_config:
        # Cho phép test cô lập DB, khóa bí mật và các cờ bảo mật.
        app.config.update(test_config)

    # Cấu hình cookie và header sớm để áp dụng cho mọi phản hồi.
    configure_cookies(app, test_config)
    init_security_headers(app)

    # Protection is always on, except that automated tests that do not
    # exercise CSRF may skip tokens. A test opts back in with
    # {"WTF_CSRF_ENABLED": True}.
    if "WTF_CSRF_ENABLED" not in app.config:
        app.config["WTF_CSRF_ENABLED"] = not app.testing

    if not app.config["SECRET_KEY"]:
        if app.testing or app.debug:
            # Secret tạm chỉ dùng trong test/phát triển, không dùng khi chạy thật.
            app.config["SECRET_KEY"] = secrets.token_hex(32)
        else:
            raise RuntimeError(
                "SECRET_KEY must be set in the environment or .env file "
                "when running outside testing or local debug mode."
            )

    # Tạo DB/seed nếu chưa có; sau đó nâng cấp schema cũ nếu cần.
    database_path = Path(app.config["DATABASE_PATH"])
    ensure_database(database_path)
    if database_path.exists():
        connection = get_connection(database_path)
        try:
            ensure_quiz_schema_columns(connection)
            ensure_login_lockout_schema(connection)
        finally:
            connection.close()

    # Blueprint chia URL theo nhóm chức năng để route không dồn vào một file.
    app.register_blueprint(auth_bp)
    app.register_blueprint(lecturer_bp)
    app.register_blueprint(quiz_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(api_bp)

    @app.before_request
    def start_request_timer():
        # Lưu thời điểm bắt đầu để tính thời gian xử lý trong log sau request.
        g.request_started_at = perf_counter()

    # Registered after start_request_timer on purpose: Flask runs before_request
    # hooks in registration order, and a rejected CSRF check must still pass
    # through log_request, which needs the timer.
    csrf.init_app(app)

    @app.after_request
    def log_request(response):
        # Route templates omit user-controlled path values; never log raw URLs,
        # query strings, headers, cookies, bodies, or response content.
        # Chỉ log đường dẫn mẫu từ Flask, tránh ghi URL/query do người dùng nhập.
        started_at = g.get("request_started_at")
        print(json.dumps({
            "event": "http_request",
            "method": request.method if request.method in {
                "GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"
            } else "OTHER",
            "path": request.url_rule.rule if request.url_rule else "<unmatched>",
            "status_code": response.status_code,
            "duration_ms": (
                None if started_at is None
                else round((perf_counter() - started_at) * 1000, 3)
            ),
        }), flush=True)
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        # error.description says why the token failed; show a fixed message.
        return render_error(400, CSRF_FAILED)

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
        # Trang gốc chuyển người dùng đến màn hình đăng nhập.
        return redirect(url_for("auth.login"))

    @app.route('/health')
    def health():
        try:
            # Read-only mode must not recreate a lost database or seed tables.
            # Kiểm tra DB chỉ đọc để health check không vô tình tạo lại dữ liệu.
            uri = Path(app.config["DATABASE_PATH"]).resolve().as_uri() + "?mode=ro"
            with closing(sqlite3.connect(uri, uri=True)) as connection:
                connection.execute('SELECT 1 FROM "user" LIMIT 1').fetchone()
        except sqlite3.Error as error:
            log_server_exception(error, 503)
            return {"status": "error", "database": "unavailable"}, 503
        return {"status": "ok", "database": "ok"}

    return app


if __name__ == '__main__':
    # Chỉ khi chạy file trực tiếp mới bật server phát triển; Gunicorn dùng factory.
    app = create_app({"DEBUG": True})
    app.run(debug=True, port=5000)
