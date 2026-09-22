# Traceability

Every screen traces back to a feature and forward to the issue that built it.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/login` | User authentication & role selection | G | P0 | F1 | [#17](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/17) | [#51](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/51) | In progress |
| `/quiz/create` | Quiz creation form | U | P0 | F2 | [#18](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/18) | [#29](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/29) | In progress |
| `/quiz/:id/questions` | Question & choice management | U | P0 | F3 | [#19](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/19) | [#47](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/47) | In progress |
| `/student/dashboard` | Student dashboard with available quiz listing | U | P0 | F4 | [#20](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/20) | [#40](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/40) | In progress |
| `/student/quiz/:id/take` | Student quiz taking screen & anti-cheat | U | P0 | F5 | [#30](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/30) | [#45](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/45) | In progress |
| `/lecturer/quiz/:id/audit` | Preserve Attempt Audit History | U | P2 | F6 | [#37](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/37) | [#41](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/41/) | In progress |
| `/student/quiz/:id/grade` | Automatic quiz grading & score result | U | P1 | F7 | [#32](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/32) | [#44](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/44) | In progress |
| `/lecturer/quiz/:id/publish` | Lecturer Publishes and Closes Quiz | U | P0 | F8 | [#34](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/34) | [#39](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/39) | In progress |
| `/lecturer/quiz/:id/time` | Set quiz duration | A | P1 | F9 | [#36](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/36) | [#48](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/48) | In progress |
| `/student/quiz/:id/submit` | Submit quiz & confirm completion | U | P0 | F10 | [#31](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/31) | [#42](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/42) | In progress |
| `/student/quiz/:id/review` | Student views quiz result | U | P1 | F11 | [#33](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/33) | [#50](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/50) | In progress |

**Access codes:** G = guest (not logged in) · U = authenticated user · A = admin

# Business Rules

| #   | Rule                                                                               | Worked example                                                                                                                      | Enforced where                                    | Tested by                            |
| --- | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- | ------------------------------------ |
| BR1 | Lecturers can only view and edit quizzes created by themselves                     | Lecturer A can edit Quiz 101 created by Lecturer A; Lecturer B receives HTTP `403` when editing Quiz 101.                           | Backend API / Quiz Controller                     | `tests/test_quiz_permissions.py`     |
| BR2 | Exam attempt records must be append-only for audit log integrity                   | After Student 25 submits Attempt 9001 with score `8/10`, changing the score to `10/10` must not modify the original record.         | Database / Attempt Service                        | `tests/test_attempt_audit.py`        |
| BR3 | Auto-grading score must be computed immediately upon submission                    | A student answering `8` of `10` questions correctly receives score `8/10` and `80%` immediately after submission.                   | Grading Engine                                    | `tests/test_auto_grading.py`         |
| BR4 | Only authenticated users with the `Admin` role may access administrative functions | An Admin can access `/admin/users`; a Lecturer requesting the same route receives HTTP `403`.                                       | Authentication middleware / Authorization service | `tests/test_admin_authorization.py`  |
| BR5 | A quiz attempt must be submitted automatically when its time limit reaches zero    | For a quiz with a `30-minute` limit started at 09:00, the system submits the attempt at 09:30 if the student has not submitted it.  | Attempt Service / Quiz Timer                      | `tests/test_quiz_time_limit.py`      |
| BR6 | A submitted quiz attempt can be finalized only once                                | If Attempt 9001 is submitted at 10:15, a repeated submission request at 10:16 must not create a second attempt or change its score. | Attempt Service / Submission API                  | `tests/test_duplicate_submission.py` |
| BR2 | Exam attempt records must be append-only for audit log integrity                   | After Student 25 submits Attempt 9001 with score `8/10`, changing the score to `10/10` must not modify the original record.         | Database / Attempt Service                        | `tests/test_attempt_audit.py`        |
| BR3 | Auto-grading score must be computed immediately upon submission                    | A student answering `8` of `10` questions correctly receives score `8/10` and `80%` immediately after submission.                   | Grading Engine                                    | `tests/test_auto_grading.py`         |
| BR4 | Only authenticated users with the `Admin` role may access administrative functions | An Admin can access `/admin/users`; a Lecturer requesting the same route receives HTTP `403`.                                       | Authentication middleware / Authorization service | `tests/test_admin_authorization.py`  |
| BR5 | A quiz attempt must be submitted automatically when its time limit reaches zero    | For a quiz with a `30-minute` limit started at 09:00, the system submits the attempt at 09:30 if the student has not submitted it.  | Attempt Service / Quiz Timer                      | `tests/test_quiz_time_limit.py`      |
| BR6 | A submitted quiz attempt can be finalized only once                                | If Attempt 9001 is submitted at 10:15, a repeated submission request at 10:16 must not create a second attempt or change its score. | Attempt Service / Submission API                  | `tests/test_duplicate_submission.py` |