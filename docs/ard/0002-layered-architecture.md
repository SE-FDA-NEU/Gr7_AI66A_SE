# ADR 0002 — Three layers: routes, services, repositories

**Status:** Accepted · Sprint 2 · Owner: @ngochien

**Context.** BR1–BR6 apply across many routes. BR5 must be checked both when
a student starts a quiz (`POST /student/quiz/<id>/take`) and when they submit
it (`POST /student/quiz/<id>/submit`). Some rules cannot be written as a
single database constraint. For example, BR3 also requires every question to
have at least two choices, which needs counting rows before a quiz is
published. Our Definition of Done requires an automated test for every story.

**Options**

1. **Everything in the route functions** in `src/app.py`: each route reads
   the request, checks the rules, runs SQL and renders the page.
2. **Three layers:** routes in `src/routes/` handle HTTP only; services in
   `src/services/` hold the business rules; repositories in
   `src/repositories/` hold all SQL.
3. **ORM models** with Flask-SQLAlchemy, putting queries and rules on model
   classes.

**Chose:** Option 2, three layers.

**Why**

- *One place for each rule.* `src/services/quiz_service.py` is the single
  module that enforces BR1–BR6 in code, so the start route and the submit
  route cannot check BR5 in two different ways. With option 1 the same check
  would be copied into several routes and drift apart over time.
- *Testable without a browser.* Service functions are plain Python. Tests
  call them directly with a temporary database, the same way
  `tests/test_init_db.py` already does. With option 1 every rule could only
  be tested through HTTP requests.
- *SQL in one place.* Only the repositories contain SQL. A schema change,
  which our process treats as high-risk, touches `src/schema.py` and the
  repositories and nothing else. This is also what keeps the move to
  PostgreSQL in ADR 1 cheap.
- *Why not an ORM.* Option 3 adds a library none of us has used and hides
  the SQL. Our schema relies on partial UNIQUE indexes for BR3 and BR5, which
  are clearer as plain SQL in `src/schema.py` than as ORM configuration.
  Learning three folders is faster for five people than learning an ORM
  mid-semester.

**What would change our mind**

- If at the end of Sprint 4 more than half of the service functions only pass
  data from the route to the repository without checking any rule, the
  service layer is not earning its place, and we will merge it into the
  routes.
- If the repositories fill up with near-identical queries whose only job is
  turning rows into objects, we will reconsider an ORM for Milestone 4 and
  record that as ADR 0003.