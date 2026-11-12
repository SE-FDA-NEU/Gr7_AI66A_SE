# Traceability

Every screen traces back to a feature and forward to the issue that built it.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/login` | User authentication & role selection | G | P0 | F1 | [#17](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/17) | [#51](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/51) | In progress |
| `/lecturer/dashboard` | Lecturer dashboard listing their quizzes | U | P1 | F12 | TODO - create issue | TODO - open PR | In pregress |
| `/quiz/create` | Quiz creation form | U | P0 | F2 | [#18](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/18) | [#29](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/29) | In progress |
| `/quiz/:id/questions` | Question & choice management | U | P0 | F3 | [#19](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/19) | [#47](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/47) | In progress |
| `/lecturer/quiz/:id/publish` | Lecturer publishes and closes a quiz | U | P0 | F8 | [#34](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/34) | [#39](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/39) | In progress |
| `/lecturer/quiz/:id/time` | Set quiz duration | U | P1 | F9 | [#36](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/36) | [#48](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/48) | In progress |
| `/lecturer/quiz/:id/audit` | Preserve attempt audit history | U | P2 | F6 | [#37](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/37) | [#41](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/41) | In progress |
| `/student/dashboard` | Student dashboard with available quiz listing | U | P0 | F4 | [#20](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/20) | [#40](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/40) | In progress |
| `/student/quiz/:id/take` | Student quiz taking screen & anti-cheat | U | P0 | F5 | [#30](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/30) | [#45](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/45) | In progress |
| `/student/quiz/:id/submit` | Submit quiz & confirm completion | U | P0 | F10 | [#31](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/31) | [#42](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/42) | In progress |
| `/student/quiz/:id/grade` | Automatic quiz grading & score result | U | P1 | F7 | [#32](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/32) | [#44](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/44) | In progress |
| `/student/quiz/:id/review` | Student views quiz result | U | P1 | F11 | [#33](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/33) | [#50](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/50) | In progress |

**US09 note:** the score for `/student/quiz/:id/grade` is shown on `/student/quiz/:id/submitted` (`Score: n/N (p%)`) instead of a separate route; see `docs/testing.md`, section US09.

## Story tests

### Issue #156: health and operational logging

`/health` is public (G). It returns HTTP 200 with
`{"status":"ok","database":"ok"}` when SQLite and the `user` table can be
queried, or HTTP 503 with `{"status":"error","database":"unavailable"}`.
The check opens SQLite read-only and closes the connection; it never creates,
repairs, or seeds the database. Issue #155 startup initialization is preserved.

Requests emit JSON to stdout with `method`, `path`, `status_code`, and
`duration_ms` (monotonic elapsed time). Paths use route templates; unmatched
paths are recorded as `<unmatched>` to exclude sensitive URL values. Query
strings, headers, cookies, request/response bodies, and session contents are
excluded. Server exceptions (including HTTP 5xx exceptions and database failures
in `/health`) emit a `server_exception` event with a filtered `stack_trace`.
Each frame contains only a project-relative file, function name, and line number;
external file paths become `<external>`. Exception messages, source lines, local
variables, notes, and chained exception text are excluded because they can contain
passwords, emails, session tokens, or quiz answers. Error responses retain their
existing status and safe content.

| Requirement | Implemented in | Tested by |
| --- | --- | --- |
| Public readiness success and empty user table | `src/app.py` | `tests/test_app.py::test_health`, `tests/test_health_logging.py::test_health_is_available_to_guest`, `test_health_accepts_empty_user_table` |
| Safe failure for missing database/table, corruption, connection error; no reseeding | `src/app.py` | `tests/test_health_logging.py::test_health_database_failure_is_safe` |
| Request fields and elapsed milliseconds on stdout | `src/app.py` | `tests/test_health_logging.py::test_request_log_fields_and_duration` |
| Safe exception handling and sensitive-data exclusion | `src/app.py` | `tests/test_health_logging.py::test_sensitive_request_data_and_exceptions_are_not_logged` |
| HTTP 5xx exception stack trace without sensitive descriptions | `src/app.py` | `tests/test_health_logging.py::test_http_server_error_logs_filtered_stack_trace` |
| Real wrong-password login returns 401 without logging credentials | `src/routes/auth_routes.py`, `src/app.py` | `tests/test_health_logging.py::test_wrong_password_login_does_not_leak_credentials` |
| Preserve HTTP error status | `src/app.py` | `tests/test_health_logging.py::test_http_errors_keep_their_status_without_exception_log` |
| Preserve question transaction rollback while returning safe HTTP 500 | `src/app.py`, existing question service | `tests/test_questions.py::test_failed_choice_insert_rolls_back_the_question` |

Run all automated tests with `python -m pytest -q`.

| Story | Route | Implemented in | Test issue | Tested by | Status |
| --- | --- | --- | --- | --- | --- |
| US09 - Student sees an automatically calculated result | `/student/quiz/:id/submitted` | `attempt_service.result_summary()`, `get_submitted_data()`, `quiz_submitted.html` | [#112](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/112) | `tests/test_us09.py` (US09-01..14 in `docs/testing.md`) | AC1, AC4 done · AC2, AC3 blocked (need `quiz.show_answers` and lecturer UI) |

**Access codes:** G = guest (not logged in) · U = authenticated user · A = administrator (not currently used by any screen - `requirements.md` has no admin persona or business rule).

# Business Rules

| # | Rule | Worked example | Enforced where | Tested by |
| --- | --- | --- | --- | --- |
| BR1 | Role-based access is enforced: a guest cannot access authenticated quiz data, a student cannot access lecturer management actions, and a lecturer cannot use student-only actions for another role | A guest requests `/student/dashboard` at 10:00; the system redirects to `/login`. A student requests `/quiz/create`; the system returns `403 Forbidden`. | Authentication middleware / route guards | `tests/test_role_based_access.py` |
| BR2 | Only the quiz owner may edit a quiz | Lecturer Ngan owns quiz Q01. At 09:00 Ngan may edit Q01; lecturer Nam requests the same edit at 09:01 and receives `403 Forbidden`, while Q01 remains unchanged. | Backend API / Quiz Controller | `tests/test_quiz_ownership.py` |
| BR3 | A quiz cannot be published unless it contains at least 1 question, every question has at least 2 choices, and exactly 1 choice is marked correct | Q02 has 2 questions; question 1 has 4 choices and 1 correct choice, question 2 has 3 choices and 0 correct choices. Publishing Q02 is rejected because the second question has 0 instead of exactly 1 correct choice. | Quiz Publish Service | `tests/test_quiz_publish_validation.py` |
| BR4 | A quiz attempt cannot continue after the configured duration or the quiz closing time, whichever comes first | A quiz opens at 09:00, closes at 10:00, and has a 20-minute duration. An attempt started at 09:45 ends at 10:00 after 15 minutes, not at 10:05. | Attempt Service / Quiz Timer | `tests/test_quiz_time_limit.py` |
| BR5 | Each student may submit up to the quiz's configured attempt limit | Lecturer sets Q03's limit to 2; Duc may submit twice, and a third attempt is rejected. | Attempt Service / Submission API | `tests/test_attempt.py::test_student_can_take_up_to_the_quiz_attempt_limit` |
| BR6 | Submitted attempts and scores are append-only: the original answers, score, and event history cannot be updated or deleted through normal application actions | A submitted 10-question attempt has score `8/10` at 15:00. At 15:05 a user tries to change it to `10/10`; the request is rejected and the audit history still contains the original `8/10` score. | Database / Attempt Service | `tests/test_attempt_audit.py` |

*This table was previously out of sync with `docs/requirements.md` (different rule text under the same BR1-BR6 IDs, plus duplicated rows). It now mirrors `requirements.md` section 5 exactly; the "Enforced where" / "Tested by" columns are this file's own addition and don't need to match anything in `requirements.md`.*
