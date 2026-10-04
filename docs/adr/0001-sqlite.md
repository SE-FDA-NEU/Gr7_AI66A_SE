# ADR 0001 — SQLite instead of PostgreSQL

**Status:** Accepted · Sprint 2 · Owner: @dnhien

**Context.** Mini LMS stores six tables: `user`, `quiz`, `question`,
`choice`, `attempt` and `answer` (Section 2). The instructor must install
and run the project on a machine we have never seen, using only
`docs/SETUP.md`. Some business rules must hold even if the application code
has a bug: BR3 (exactly one correct choice per question), BR5 (at most one
submitted attempt per student and quiz) and BR6 (submitted attempts are
never changed).

**Options**

1. **SQLite file** (`data/minilms.db`), opened with Python's built-in
   `sqlite3` module.
2. **PostgreSQL in Docker**, opened with the `psycopg` driver.
3. **CSV files** read into memory when the app starts and written back on
   every change.

**Chose:** Option 1, SQLite.

**Why**

- *Setup on an unknown machine.* SQLite ships with Python, so SETUP.md lists
  only Git and Python 3.11+ as prerequisites. PostgreSQL would add Docker
  Desktop: a large download that often needs virtualisation enabled in the
  BIOS on Windows laptops. That puts the 15-minute setup at risk for no
  benefit at our scale.
- *Rules enforced by the database, not only by code.* SQLite supports
  FOREIGN KEY, CHECK and partial UNIQUE indexes. `src/schema.py` uses
  `one_correct_choice_per_question` to enforce part of BR3 and
  `one_submitted_attempt_per_student_quiz` to enforce BR5, and `src/db.py`
  turns on `PRAGMA foreign_keys = ON` for every connection. CSV files
  (option 3) cannot enforce any of these rules. Two students saving at the
  same time could also overwrite each other's file, so option 3 was
  rejected.
- *Data size.* One course has at most a few hundred students. Even
  300 students × 20 quizzes × 20 questions is about 120,000 `answer` rows,
  which a single SQLite file handles comfortably.
- *Fast, real tests.* Each test creates a fresh database in a temporary
  folder, runs the real schema and loads the 97 seed rows. The current suite
  of 7 tests finishes in about 0.1 s, so CI can test real SQL on every pull
  request.

**What would change our mind**

- If a test with 30 students submitting at the same moment produces
  `database is locked` errors or a lost submission, we will move to
  PostgreSQL in Sprint 4. Because only `src/db.py` and the repositories touch
  the database (ADR 2), the change stays inside those files.
- If the staging server we deploy to cannot keep a file between restarts,
  SQLite would lose data there, and we would switch to a hosted PostgreSQL.