"""SQLite schema for the MiniLMS data model."""

SCHEMA_SQL = """
DROP TABLE IF EXISTS answer;
DROP TABLE IF EXISTS attempt;
DROP TABLE IF EXISTS choice;
DROP TABLE IF EXISTS question;
DROP TABLE IF EXISTS quiz;
DROP TABLE IF EXISTS user;

CREATE TABLE user (
    user_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('lecturer', 'student', 'ta'))
);

CREATE TABLE quiz (
    quiz_id INTEGER PRIMARY KEY,
    lecturer_id INTEGER NOT NULL REFERENCES user(user_id),
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'published', 'closed')),
    duration_minutes INTEGER NOT NULL CHECK (duration_minutes > 0),
    start_at TEXT,
    end_at TEXT,
    CHECK (start_at IS NULL OR end_at IS NULL OR end_at > start_at)
);

CREATE TABLE question (
    question_id INTEGER PRIMARY KEY,
    quiz_id INTEGER NOT NULL REFERENCES quiz(quiz_id),
    content TEXT NOT NULL,
    points INTEGER NOT NULL CHECK (points > 0),
    position INTEGER NOT NULL CHECK (position > 0),
    UNIQUE (quiz_id, position)
);

CREATE TABLE choice (
    choice_id INTEGER PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES question(question_id),
    content TEXT NOT NULL,
    is_correct INTEGER NOT NULL CHECK (is_correct IN (0, 1))
);

CREATE UNIQUE INDEX one_correct_choice_per_question
    ON choice(question_id) WHERE is_correct = 1;

CREATE TABLE attempt (
    attempt_id INTEGER PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES user(user_id),
    quiz_id INTEGER NOT NULL REFERENCES quiz(quiz_id),
    started_at TEXT NOT NULL,
    submitted_at TEXT,
    score REAL
);

CREATE UNIQUE INDEX one_submitted_attempt_per_student_quiz
    ON attempt(student_id, quiz_id) WHERE submitted_at IS NOT NULL;

CREATE TABLE answer (
    answer_id INTEGER PRIMARY KEY,
    attempt_id INTEGER NOT NULL REFERENCES attempt(attempt_id),
    question_id INTEGER NOT NULL REFERENCES question(question_id),
    choice_id INTEGER REFERENCES choice(choice_id),
    UNIQUE (attempt_id, question_id)
);
"""

TABLE_NAMES = ("user", "quiz", "question", "choice", "attempt", "answer")
