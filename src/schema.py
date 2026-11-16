"""Định nghĩa schema SQLite: các bảng, ràng buộc toàn vẹn và trigger của MiniLMS."""
from __future__ import annotations

SCHEMA_SQL = """
-- Xóa các bảng phụ thuộc trước, rồi mới xóa bảng cha để reset đúng thứ tự khóa ngoại.
DROP TABLE IF EXISTS attempt_audit;
DROP TABLE IF EXISTS answer;
DROP TABLE IF EXISTS attempt;
DROP TABLE IF EXISTS choice;
DROP TABLE IF EXISTS question;
DROP TABLE IF EXISTS quiz;
DROP TABLE IF EXISTS client_lockout;
DROP TABLE IF EXISTS login_lockout;
DROP TABLE IF EXISTS login_failure;
DROP TABLE IF EXISTS user;

-- Tài khoản dùng chung cho giảng viên, sinh viên và trợ giảng.
CREATE TABLE user (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('lecturer', 'student', 'ta'))
);

-- Lưu các lần đăng nhập sai để giới hạn thử lại theo tài khoản và client.
CREATE TABLE login_failure (
    failure_id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    client_key TEXT NOT NULL DEFAULT '',
    failed_at INTEGER NOT NULL
);

CREATE INDEX login_failure_email_failed_at
    ON login_failure(email, client_key, failed_at);

CREATE INDEX login_failure_client_failed_at
    ON login_failure(client_key, failed_at);

CREATE INDEX login_failure_failed_at
    ON login_failure(failed_at);

-- Lock one client out of one account (BR: 5 failures in 10 min -> 15 min).
CREATE TABLE login_lockout (
    email TEXT NOT NULL,
    client_key TEXT NOT NULL DEFAULT '',
    locked_until INTEGER NOT NULL,
    PRIMARY KEY (email, client_key)
);

-- Lock one client out of the whole login form (many different accounts tried).
CREATE TABLE client_lockout (
    client_key TEXT PRIMARY KEY,
    locked_until INTEGER NOT NULL
);

-- Quiz thuộc một giảng viên; CHECK giữ trạng thái và giới hạn thời gian hợp lệ.
CREATE TABLE quiz (
    quiz_id INTEGER PRIMARY KEY,
    lecturer_id INTEGER NOT NULL REFERENCES user(user_id),
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'closed')),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    duration_unlimited INTEGER NOT NULL DEFAULT 0
        CHECK (duration_unlimited IN (0, 1)),
    max_attempts INTEGER NOT NULL DEFAULT 1 CHECK (max_attempts > 0),
    last_published_end_at TEXT,
    closed_by_deadline INTEGER NOT NULL DEFAULT 0
        CHECK (closed_by_deadline IN (0, 1)),
    start_at TEXT,
    end_at TEXT,
    CHECK (start_at IS NULL OR end_at IS NULL OR end_at > start_at)
);

-- Câu hỏi thuộc quiz, vị trí không trùng trong cùng một quiz.
CREATE TABLE question (
    question_id INTEGER PRIMARY KEY,
    quiz_id INTEGER NOT NULL REFERENCES quiz(quiz_id),
    content TEXT NOT NULL,
    points INTEGER NOT NULL CHECK (points > 0),
    position INTEGER NOT NULL CHECK (position > 0),
    UNIQUE (quiz_id, position)
);

-- Lựa chọn thuộc câu hỏi; partial unique index giới hạn một đáp án đúng.
CREATE TABLE choice (
    choice_id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES question(question_id),
    content TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1))
);

CREATE UNIQUE INDEX one_correct_choice_per_question
    ON choice(question_id) WHERE is_correct = 1;

-- Mỗi lần làm bài gắn một sinh viên với một quiz.
CREATE TABLE attempt (
    attempt_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES user(user_id),
    quiz_id INTEGER NOT NULL REFERENCES quiz(quiz_id),
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    score REAL
);

-- Mỗi câu trong một lượt làm bài chỉ có một lựa chọn được lưu.
CREATE TABLE answer (
    answer_id INTEGER PRIMARY KEY,
    attempt_id INTEGER NOT NULL REFERENCES attempt(attempt_id),
    question_id INTEGER NOT NULL REFERENCES question(question_id),
    choice_id INTEGER REFERENCES choice(choice_id),
    UNIQUE (attempt_id, question_id)
);

-- Nhật ký ghi lại các hành động quan trọng để truy vết lịch sử làm bài.
CREATE TABLE attempt_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    attempt_id INTEGER NOT NULL REFERENCES attempt(attempt_id) ON DELETE CASCADE,
    actor_id INTEGER NOT NULL REFERENCES user(user_id),
    action TEXT NOT NULL CHECK (
        action IN (
            'ATTEMPT_STARTED',
            'ANSWER_SAVED',
            'ATTEMPT_SUBMITTED',
            'AUTO_SUBMITTED',
            'GRADE_OVERRIDDEN'
        )
    ),
    metadata TEXT, -- JSON string
    timestamp TEXT NOT NULL
);

CREATE INDEX idx_attempt_audit_attempt_id
    ON attempt_audit(attempt_id, timestamp ASC);

-- Enforce Immutability (Append-Only) via Database Triggers
CREATE TRIGGER prevent_attempt_audit_update
BEFORE UPDATE ON attempt_audit
BEGIN
    SELECT RAISE(FAIL, 'IMMUTABLE_RECORD: Attempt audit history logs cannot be modified.');
END;

CREATE TRIGGER prevent_attempt_audit_delete
BEFORE DELETE ON attempt_audit
BEGIN
    SELECT RAISE(FAIL, 'IMMUTABLE_RECORD: Attempt audit history logs cannot be deleted.');
END;
"""

TABLE_NAMES = ("user", "quiz", "question", "choice", "attempt", "answer", "attempt_audit")