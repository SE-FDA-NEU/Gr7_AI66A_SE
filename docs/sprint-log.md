# Sprint log

One section per sprint. Fill it in **during** the sprint, not the night before
the milestone deadline - the commit timestamps on this file are part of the
evidence that the process was real.

---

## Sprint 1 - 2026-09-08 to 2026-09-22

### Sprint goal

Deliver the P0 slice of `docs/requirements.md`: sign-in with role routing (US01),
lecturer quiz creation and publishing (US02-US04), and the student's ability to
start and submit an attempt (US06, US08).

### Two mandatory chore issue

| Issue                               | Assignee     | Closed? |
| ----------------------------------- | ------------ | ------- |
| [Chore] Refine backlog for Sprint 1 | @anhthu (PO) | Yes     |
| [Chore] Sprint 1 wrap-up            | @nganan (SM) | Yes     |

### Committed

| Issue | Story                                                 | Story ID               | Points | Owner     |
| ----- | ----------------------------------------------------- | ---------------------- | ------ | --------- |
| #1    | [Chore] Refine backlog for Sprint 1                   | -                      | 2      | @anhthu   |
| #2    | [Chore] Sprint 1 wrap-up                              | -                      | 2      | @nganan   |
| #3    | [Story] User Authentication & Role Separation         | US01 (P0)              | 3      | @tuekhang |
| #4    | [Story] Lecturer Quiz Creation & Management           | US02 (P0)              | 5      | @thanhlan |
| #5    | [Story] Add Multiple-Choice Questions to Quiz         | US03 (P0)              | 5      | @ngochien |
| #6    | [Story] Student Quiz Listing & Attempt Initialization | US05 (P1) + US06 (P0)  | 6      | @tuekhang |
| #7    | [Spike] Prototype Quiz-Taking UI & Anti-Cheat Rules   | relates to US06 / US13 | 3      | @ngochien |

**Total committed: 26 points**
copy lại bảng từ traceability.md vào đây

### Result

| Issue | Points | Status | If not done, why |
| ----- | ------ | ------ | ---------------- |
| #1    | 2      | TBD    |                  |
| #2    | 2      | TBD    |                  |
| #3    | 3      | TBD    |                  |
| #4    | 5      | TBD    |                  |
| #5    | 5      | TBD    |                  |
| #6    | 6      | TBD    |                  |
| #7    | 3      | TBD    |                  |

**Completed: `<fill in at end of sprint>` points. Velocity this sprint: `<fill in at end of sprint>`**

_Fill this table in with the real status of each issue on the Sunday before
submission - "TBD" and "In progress" for every row is not acceptable for the
milestone (it requires committed, completed, and velocity as actual figures)._

### Sprint Review

- What we demonstrated: TBD at end of sprint
- Feedback received: TBD at end of sprint
- Backlog changes as a result: TBD at end of sprint

### Retrospective

| Keep doing | Stop doing | Start doing |
| ---------- | ---------- | ----------- |
| TBD        | TBD        | TBD         |

**One concrete action for next sprint (with an owner):** TBD at Sprint 1 Retro

### Attendance

| Member    | Planning | Review | Retro |
| --------- | -------- | ------ | ----- |
| @anhthu   | Yes      |        |       |
| @nganan   | Yes      |        |       |
| @ngochien | Yes      |        |       |
| @thanhlan | Yes      |        |       |
| @tuekhang | Yes      |        |       |

---

## Sprint 2 - 2026-09-23 to 2026-10-04

### Sprint goal

Prove the architecture end to end for Milestone 2: a walking skeleton
(`GET /student/dashboard` showing 12 published quizzes read from SQLite),
the design document (`docs/design.md`, six sections, two ADRs in `docs/adr/`)
and a setup guide that runs on a clean machine (`docs/SETUP.md`).

### Two mandatory chore issue

| Issue                                   | Assignee         | Closed?                 |
| --------------------------------------- | ---------------- | ----------------------- |
| #59 [Chore] Refine backlog for Sprint 2 | @anhthu0910 (PO) | Yes                     |
| #58 [Chore] Sprint 2 wrap-up            | @dnghien (SM)    | Yes (closed by this PR) |

### Committed (Sprint Planning, 2026-09-29)

| Issue | Story                                                              | Story ID | Points | Owner               |
| ----- | ------------------------------------------------------------------ | -------- | ------ | ------------------- |
| #58   | [Chore] Sprint 2 wrap-up                                           | -        | 2      | @dnghien            |
| #59   | [Chore] Refine backlog for Sprint 2                                | -        | 2      | @anhthu0910         |
| #57   | [Chore] Design ERD                                                 | -        | 3      | @nganannn           |
| #60   | [Chore] design.md Section 1 architecture and Section 5 ADRs        | -        | 3      | @dnghien            |
| #61   | [Chore] design.md Section 3 API and Section 6 changes since M1     | -        | 3      | @anhthu0910         |
| #62   | [Chore] Design walking skeleton GET /student/dashboard (Section 4) | US05     | 3      | @ngthanhlan06-droid |
| #63   | [Chore] Writing design decisions                                   | -        | 2      | -                   |

**Total committed: 18 points**

_Points use the Sprint 1 scale: chore = 2, one design.md section = 3,
database work = 5. They were set during backlog refinement._

### Scope changes during the sprint

- **2026-10-03 — re-planning.** Once the walking-skeleton route and the
  database tables were agreed, the remaining work was split so that every
  member owned one issue and one pull request: #65 ERD and schema (3),
  #66 schema/seed/init_db (5), #67 SETUP.md (2), #68 test SETUP.md on a clean
  machine (1), #69 Flask scaffold and CI (3), #70 US05 walking skeleton (3).
  Added scope: 17 points.
- **#63 closed as not planned** — merged into #60, which already covers the ADRs.
- Requirement changes this sprint are recorded in `docs/design.md` Section 6
  and `docs/changelog.md`.

### Result

| Issue               | Points | Status                                                                 | If not done, why |
| ------------------- | ------ | ---------------------------------------------------------------------- | ---------------- |
| #57                 | 3      | Done — PR #64                                                          |                  |
| #60                 | 3      | Done — PR #76                                                          |                  |
| #61                 | 3      | Done — PR #77                                                          |                  |
| #62                 | 3      | Done — PR #75                                                          |                  |
| #63                 | 2      | Closed, not planned                                                    | Merged into #60  |
| #59                 | 2      | Done                                                                   |                  |
| #58                 | 2      | Done — this PR                                                         |                  |
| #65 _(added 10-03)_ | 3      | Done — PR #73                                                          |                  |
| #66 _(added 10-03)_ | 5      | Done — PR #74                                                          |                  |
| #69 _(added 10-03)_ | 3      | Done — PR #72                                                          |                  |
| #70 _(added 10-03)_ | 3      | Done — PR #75                                                          |                  |
| #67 _(added 10-03)_ | 2      | Done — PR #71, updated to the final route and tables in a follow-up PR |                  |
| #68 _(added 10-03)_ | 1      | Done — "Tested by" record in SETUP.md                                  |                  |

**Completed: 33 points (16 of 18 committed + 17 added). Velocity this sprint: 33**

### Sprint Review

- What we demonstrated: a fresh clone set up by following `docs/SETUP.md`;
  `python src/init_db.py` creates 6 tables and seeds 97 rows;
  `http://localhost:5000/student/dashboard` lists 12 published quizzes with
  drafts hidden (US05); 8 automated tests pass in CI; `docs/design.md`
  complete with six sections and two ADRs.
- Feedback received: reviews asked for each requirement change in Section 6 to
  state its reason, and for SETUP.md to be checked against the final code;
  CI held back the database PR until it included the shared schema.
- Backlog changes as a result: US03 acceptance criterion aligned with BR3
  (at least 2 options, exactly 1 correct); Sprint 3 adds the BR1 login guard to
  `/student/dashboard` together with US01.

### Retrospective

| Keep doing                                               | Stop doing                                             | Start doing                                                           |
| -------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| One issue, one branch, one PR per member                 | Merging before every review comment is resolved        | Estimating points and taking a board screenshot at Sprint Planning    |
| CI on every PR — it caught a missing schema before merge | Letting any commit reach `main` without a pull request | Running SETUP.md on a teammate's machine before merging setup changes |
| Reviews with "Review changes" and a concrete comment     | Writing setup steps before the code they describe      | Adding label and milestone when an issue is created                   |

**One concrete action for next sprint (with an owner):** At Sprint 3 Planning,
estimate every issue on the board and commit a board screenshot to
`docs/sprint-log.md` the same day · @dnghien (hands over to the Sprint 3 SM)

### Attendance

| Member              | Planning | Review | Retro |
| ------------------- | -------- | ------ | ----- |
| @anhthu0910         | Yes      | Yes    | Yes   |
| @nganannn           | Yes      | Yes    | Yes   |
| @dnghien            | Yes      | Yes    | Yes   |
| @ngthanhlan06-droid | Yes      | Yes    | Yes   |
| @khangtrannf        | Yes      | Yes    | Yes   |

---

## Sprint 3 - 2026-10-05 to 2026-10-19

### Sprint goal

Deliver the core Mini LMS workflows end to end: secure sign-in and role-based
access (US01), lecturer quiz creation, question management, publishing and
closing (US02-US04), and student quiz discovery, attempt, review and submission
(US05-US08). Complete the lecturer and student dashboards, cover the main
validation and error states, and verify that a new team member can set up the
project from `docs/SETUP.md`.

### Two mandatory chore issue

| Issue                                   | Assignee          | Closed?                         |
| --------------------------------------- | ----------------- | ------------------------------- |
| #82 [Chore] Refine backlog for Sprint 3 | @anhthu0910 (PO)  | Yes                             |
| #83 [Chore] Sprint 3 wrap-up            | @khangtrannf (SM) | Yes (wrap-up PR number pending) |

### Committed

| Issue | Story                                                       | Story ID  | Points | Owner               |
| ----- | ----------------------------------------------------------- | --------- | ------ | ------------------- |
| #82   | [Chore] Refine backlog for Sprint 3                         | -         | 2      | @anhthu0910         |
| #83   | [Chore] Sprint 3 wrap-up                                    | -         | 2      | @khangtrannf        |
| #84   | [Chore] Test SETUP.md on a clean machine                    | -         | 1      | @ngthanhlan06-droid |
| #85   | [Chore] Implement the student dashboard with four UI states | US05      | 3      | @dnghien            |
| #86   | [Chore] Implement a minimal lecturer dashboard              | US14      | 3      | @nganannn           |
| #87   | [Task] US08: Review and submit a quiz attempt               | US08 (P0) | 3      | @dnghien            |
| #88   | [Task] US06: Start a quiz attempt                           | US06 (P0) | 3      | @dnghien            |
| #89   | [Task] US04: Publish and close a quiz                       | US04 (P0) | 3      | @anhthu0910         |
| #90   | [Task] US03: Add questions to a quiz                        | US03 (P0) | 5      | @ngthanhlan06-droid |
| #91   | [Task] US02: Create a quiz                                  | US02 (P0) | 5      | @nganannn           |
| #92   | [Task] US01: Implement login, role-based access, and logout | US01 (P0) | 3      | @khangtrannf        |

**Total committed: 33 points**

_The GitHub issues do not record point estimates. For this reconstructed log,
story tasks use the estimates in `docs/requirements.md`; chores use the Sprint
2 calibration (2 points for backlog refinement and wrap-up, 1 for clean-setup
verification, and 3 for each dashboard implementation). Confirm these estimates
against the Sprint 3 planning record if one is available._

### Scope changes during the sprint

- Supporting UI documentation and wireframes were merged in PRs #96, #98,
  #101 and #102. The lecturer dashboard implementation was merged in PR #105.
  No additional issue points are counted for these supporting documents.
- No other scope changes are recorded in the repository.

### Result

| Issue | Points | Status                                           | If not done, why |
| ----- | ------ | ------------------------------------------------ | ---------------- |
| #82   | 2      | Done — backlog refinement                        |                  |
| #83   | 2      | Done — Sprint 3 wrap-up (this PR)                |                  |
| #84   | 1      | Done — clean-machine setup test passed - PR #106 |                  |
| #85   | 3      | Done — PR #100                                   |                  |
| #86   | 3      | Done — PR #105                                   |                  |
| #87   | 3      | Done — PR #97                                    |                  |
| #88   | 3      | Done — PR #94                                    |                  |
| #89   | 3      | Done — PR #95                                    |                  |
| #90   | 5      | Done — PR #99                                    |                  |
| #91   | 5      | Done — PR #103                                   |                  |
| #92   | 3      | Done — PR #93                                    |                  |

**Completed: 33 points (all 33 committed, assuming all Sprint 3 tasks are complete). Velocity this sprint: 33**

### Sprint Review

- What we demonstrated: role-specific login and logout, access control and
  account lockout after repeated failed logins; lecturer quiz creation,
  question validation, publishing and closing; and student dashboard states,
  starting/resuming an attempt, reviewing unanswered questions, and submitting
  once. The changes also add automated coverage for authentication, database
  initialization and dashboard behavior.
- Feedback received: Not recorded in the repository; confirm with the team
  before submission.
- Backlog changes as a result: No follow-up backlog changes are recorded.

### Retrospective

_Drafted from the repository changes; validate these points with the team
before treating them as the outcomes of the Sprint 3 retrospective._

| Keep doing                                                  | Stop doing                                                                                | Start doing                                                                              |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Keep work tied to planned issues and reviewed pull requests | Treating a merged wireframe as proof that the corresponding UI implementation is complete | Verify every acceptance criterion across lecturer and student roles before sprint review |
| Add automated tests alongside behavior changes              | Leaving clean-machine setup verification until wrap-up                                    | Complete and record clean-machine setup verification earlier in the sprint               |
| Preserve clear user-facing errors for rejected actions      |                                                                                           |                                                                                          |

**Clean-machine verification:** `docs/SETUP.md` and the end-to-end role
workflows were tested successfully

### Attendance

| Member              | Planning | Review | Retro |
| ------------------- | -------- | ------ | ----- |
| @anhthu0910         | Yes      | Yes    | Yes   |
| @nganannn           | Yes      | Yes    | Yes   |
| @dnghien            | Yes      | Yes    | Yes   |
| @ngthanhlan06-droid | Yes      | Yes    | Yes   |
| @khangtrannf        | Yes      | Yes    | Yes   |
