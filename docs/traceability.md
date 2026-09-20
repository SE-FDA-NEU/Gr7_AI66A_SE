# Traceabilityệ

Every screen traces back to a feature and forward to the issue that built it.
| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/login` | User authentication & role selection | G | P0 | F1 | [#17](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/17) | - | In progress |
| `/lecturer/dashboard` | Lecturer dashboard & quiz list | U | P0 | F2 | #4 | - | In progress |
| `/quiz/create` | Quiz creation form | U | P0 | F2 | [#18](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/18) | - | In progress |
| `/quiz/:id/questions` | Question & choice management | U | P0 | F3 | #5 | - | In progress |
| `/student/dashboard` | Student dashboard & quiz listing | U | P0 | F4 | [#20](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/20) | - | In progress |
| `/student/quiz/:id/take` | Student quiz taking screen & anti-cheat | U | P0 | F4 | #6 | - | In progress |
| `/student/quiz/:id/take` | Student quiz taking screen & anti-cheat | U | P0 | F4 | #6 | - | In progress |

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
