# Traceability

Every screen traces back to a feature and forward to the issue that built it.
| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/login` | User authentication & role selection | G | P0 | F1 | [#17](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/17) | - | In progress |
| `/lecturer/dashboard` | Lecturer dashboard & quiz list | U | P0 | F2 | #4 | - | In progress |
| `/quiz/create` | Quiz creation form | U | P0 | F3 | [#18](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/18) | - | In progress |
| `/quiz/:id/questions` | Question & choice management | U | P0 | F4 | #5 | - | In progress |
| `/student/dashboard` | Student dashboard & quiz listing | U | P0 | F5 | [#20](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/20) | - | In progress |
| `/student/quiz/:id/take` | Student quiz taking screen & anti-cheat | U | P0 | F6 | #6 | - | In progress |
| `/lecturer/quiz/:id/time` | Set quiz duration | A | P1 | F7 | [#36](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/36) | [#48](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/48) | In progress |
| `/student/quiz/:id/submit` | Submit quiz & confirm completion | U | P0 | F8 | [#31](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/31) | [#42](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/42) | In progress |

# Business Rules

**Access codes:** G = guest (not logged in) · U = authenticated user · A = admin
| # | Rule | Enforced where | Tested by |
|---|------|----------------|-----------|
| BR1 | Lecturers can only view and edit quizzes created by themselves | Backend API / Quiz Controller | `tests/test_quiz_permissions.py` |
| BR2 | Exam attempt records must be append-only for audit log integrity | Database / Attempt Service | `tests/test_attempt_audit.py` |
| BR3 | Auto-grading score must be computed immediately upon submission | Grading Engine | `tests/test_auto_grading.py` |
