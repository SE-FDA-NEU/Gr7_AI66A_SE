# Traceability

Every screen traces back to a feature and forward to the issue that built it.

| Route | Purpose | Access | Priority | Feature | Story issue | PR | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `/login` | User authentication & role selection | G | P0 | F1 | [#51](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/51) | - | In progress |
| `/lecturer/dashboard` | Lecturer dashboard & quiz list | U | P0 | F2 | #4 | - | In progress |20-quiz-listing
| `/quiz/create` | Quiz creation form | U | P0 | F3 | [#18](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/18) | - | In progress |
| `/quiz/:id/questions` | Question & choice management | U | P0 | F4 | #5 | - | In progress |
| `/student/dashboard` | Student dashboard with available quiz listing | U | P0 | F5 | [#20](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/20) | [#40](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/40) | In progress |
| `/student/quiz/:id/take` | Student quiz taking screen & anti-cheat | U | P0 | F6 | #6 | - | In progress |
| `/quiz/create` | Quiz creation form | U | P0 | F2 | [#18](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/18) | - | In progress |
| `/quiz/:id/questions` | Question & choice management | U | P0 | F3 | [#19](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/19) | [#47](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/47) | In progress |
| `/student/dashboard` | Student dashboard & quiz listing | U | P0 | F4 | [#20](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/20) | - | In progress |
| `/student/dashboard` | Student dashboard & quiz listing | U | P0 | F4 | [#35](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/35) | [#43](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/43) | In progress |
| `/student/quiz/:id/take` | Student quiz taking screen & anti-cheat | U | P0 | F4 | [#30](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/30) | [#45](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/45) | In progress |
| `/lecturer/quiz/:id/audit` | Preserve Attempt Audit History | U | P2 | F5 | [#37](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/37) | [#41](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/41/) | In progress |
| `/student/quiz/:id/grade` | Automatic quiz grading & score result | U | P1 | F4 | [#32](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/32) | [#44](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/44) | In progress |
| `/lecturer/quiz/:id/publish` | Lecturer Publishes and Closes Quiz | U | P0 | F5 | [#34](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/34) | [#39](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/39) | In progress |
| `/lecturer/quiz/:id/time` | Set quiz duration | A | P1 | F7 | [#36](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/36) | [#48](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/48) | In progress |
| `/student/quiz/:id/submit` | Submit quiz & confirm completion | U | P0 | F8 | [#31](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/31) | [#42](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/42) | In progress |
| `/student/quiz/:id/review` | Student views quiz result | U | P1 | F9 | [#33](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/33) | [#50](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/50) | In progress |
| `/admin/users` | Admin Manages User Accounts and Roles | A | P0 | F10 | [#49](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/49) | [#50](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/50) | In progress |

# Business Rules

**Access codes:** G = guest (not logged in) · U = authenticated user · A = admin

| # | Rule | Enforced where | Tested by |
|---|------|----------------|-----------|
| BR1 | Lecturers can only view and edit quizzes created by themselves | Backend API / Quiz Controller | `tests/test_quiz_permissions.py` |
| BR2 | Exam attempt records must be append-only for audit log integrity | Database / Attempt Service | `tests/test_attempt_audit.py` |
| BR3 | Auto-grading score must be computed immediately upon submission | Grading Engine | `tests/test_auto_grading.py` |