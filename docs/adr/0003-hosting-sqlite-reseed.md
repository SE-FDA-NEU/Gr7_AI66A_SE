# ADR 0003 — Keep SQLite on Render and reseed when the database is missing

**Status:** Proposed · Sprint 4 · Owner: @dnghien

**Document:** ADR 0003 · Version 1.0 · 2026-11-10

**Context.** We deploy Mini LMS on Render's free plan. Its disk is wiped on
every restart and redeploy, and `data/minilms.db` is in `.gitignore`. A fresh
server therefore starts with no database, and the first request fails. We
cannot fix this by calling `init_db()` on every start-up: `src/schema.py`
begins with `DROP TABLE IF EXISTS`, so that would erase all data each time the
app starts. ADR 0001 already said that a server which cannot keep a file
between restarts would make us reconsider SQLite.

**Options**

1. **Hosted PostgreSQL** (Neon or Supabase free tier), opened with the
   `psycopg` driver. Data survives restarts.
2. **A paid persistent disk** on Render, mounted at the folder that holds
   `minilms.db`. SQLite stays as it is and the file survives restarts.
3. **SQLite + reseed on start-up.** `create_app()` calls
   `ensure_database(db_path)` from `src/init_db.py`. It creates the parent
   folder, and runs `init_db()` only when the file is missing or has no
   `user` table. A database that already has data is never touched.

**Chose:** Option 3, SQLite + reseed.

**Why**

- *No new cost or account.* Option 2 needs a paid plan. Option 1 needs a new
  external account and secret, which the instructor would also have to set up.
- *No rewrite late in the project.* Option 1 means changing the driver, the
  SQL dialect (`BEGIN IMMEDIATE`, partial UNIQUE indexes, triggers) and the
  test fixtures in Sprint 4. Option 3 adds one function and one line in
  `create_app()`.
- *Same behaviour locally and in tests.* The deployed demo always starts from
  the same 97 seed rows that the tests and `docs/SETUP.md` use, so a demo
  account always works after a restart.
- *Safe by construction.* `tests/test_ensure_database.py` checks that a
  missing database is seeded (ED01), that an existing one is not reseeded
  (ED02), and that nested missing folders are created (ED03). Replacing the
  guard with `if False` makes ED02 fail, so the test really protects the data.

**Consequences**

- Any data created on the deployed server (new quizzes, attempts, edited
  titles, lockouts) is **lost on every restart or redeploy**. The staging
  server is a demo, not a place to keep real course data.
- Local development is unchanged: an existing `data/minilms.db` is left as it
  is.
- A database that has some tables but no `user` table is treated as empty
  and reseeded.
- This ADR records the outcome of ADR 0001's second "What would change our
  mind" point: we hit that case and kept SQLite for now instead of moving to
  hosted PostgreSQL.

**What would change this decision**

- If real users (students or lecturers) start to depend on the deployed
  server, losing their data on restart is no longer acceptable. We would move
  to option 1 (hosted PostgreSQL) or option 2 (persistent disk).
- If the team gets a paid Render plan, option 2 becomes the cheapest fix,
  because it keeps SQLite and needs no code change.
- If the ADR 0001 concurrency test (30 students submitting at once) fails,
  we move to PostgreSQL anyway, and this reseed step becomes a one-off seeding
  script.
