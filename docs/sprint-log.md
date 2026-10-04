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

| Issue | Assignee | Closed? |
| --- | --- | --- |
| [Chore] Refine backlog for Sprint 1 | @anhthu (PO) | Yes |
| [Chore] Sprint 1 wrap-up | @nganan (SM) | Yes |

### Committed

| Issue | Story | Story ID | Points | Owner |
|-------|-------|----------|--------|-------|
| #1 | [Chore] Refine backlog for Sprint 1 | - | 2 | @anhthu |
| #2 | [Chore] Sprint 1 wrap-up | - | 2 | @nganan |
| #3 | [Story] User Authentication & Role Separation | US01 (P0) | 3 | @tuekhang |
| #4 | [Story] Lecturer Quiz Creation & Management | US02 (P0) | 5 | @thanhlan |
| #5 | [Story] Add Multiple-Choice Questions to Quiz | US03 (P0) | 5 | @ngochien |
| #6 | [Story] Student Quiz Listing & Attempt Initialization | US05 (P1) + US06 (P0) | 6 | @tuekhang |
| #7 | [Spike] Prototype Quiz-Taking UI & Anti-Cheat Rules | relates to US06 / US13 | 3 | @ngochien |

**Total committed: 26 points**
copy lại bảng từ traceability.md vào đây

### Result

| Issue | Points | Status | If not done, why |
|-------|--------|--------|------------------|
| #1 | 2 | TBD | |
| #2 | 2 | TBD | |
| #3 | 3 | TBD | |
| #4 | 5 | TBD | |
| #5 | 5 | TBD | |
| #6 | 6 | TBD | |
| #7 | 3 | TBD | |

**Completed: `<fill in at end of sprint>` points. Velocity this sprint: `<fill in at end of sprint>`**

*Fill this table in with the real status of each issue on the Sunday before
submission - "TBD" and "In progress" for every row is not acceptable for the
milestone (it requires committed, completed, and velocity as actual figures).*

### Sprint Review

- What we demonstrated: TBD at end of sprint
- Feedback received: TBD at end of sprint
- Backlog changes as a result: TBD at end of sprint

### Retrospective

| Keep doing | Stop doing | Start doing |
|------------|------------|-------------|
| TBD | TBD | TBD |

**One concrete action for next sprint (with an owner):** TBD at Sprint 1 Retro

### Attendance

| Member | Planning | Review | Retro |
| --- | --- | --- | --- |
| @anhthu | Yes |  |  |
| @nganan | Yes |  |  |
| @ngochien | Yes |  |  |
| @thanhlan | Yes |  |  |
| @tuekhang | Yes |  |  |


---

## Sprint 2 - 2026-09-23 to 2026-10-04

### Sprint goal

### What Changed Since Milestone 1

#### Change 1: Added Lecturer Dashboard (US14)
* **What changed:** Introduced a new user story **US14 (Lecturer Dashboard)** and its corresponding route `/lecturer/dashboard`.
* **Reason:** During Sprint 2 architecture design, we identified that lecturers required a centralized interface to view, edit, and track attempt counts for all quizzes they own.
* **Affected Story / BR:** US14 & BR1 (Role-based access).
* **Reference:** Issue #68 (Commit: "New route for new US14").

#### Change 2: Aligned US03 Acceptance Criteria with BR3 and Database Schema
* **What changed:** Updated the acceptance criteria for **US03** (Lecturer adds multiple-choice questions) from requiring "exactly 4 options" to "at least 2 options".
* **Reason:** Resolved a contradiction between Milestone 1 (where US03 strictly mandated 4 choices) and Business Rule BR3 / `CHOICE` database schema (which permits flexible choice counts with a minimum of 2 options).
* **Affected Story / BR:** US03, BR3, and `CHOICE` table constraint.
* **Reference:** Issue #69.

#### Change 3: Added TA Persona (Mai) and Read-Only Audit Access
* **What changed:** Added persona **Mai (Teaching Assistant)** with dedicated read-only permission to view quiz attempt audit logs (`/lecturer/quiz/:id/audit`).
* **Reason:** Feedback from the Sprint 1 Review highlighted the need for TAs to investigate student grading disputes without granting full editing/publishing authority over quizzes.
* **Affected Story / BR:** US12 (Attempt audit history) & BR1.
* **Reference:** Issue #70.

### Two mandatory chore issue

| Issue | Assignee | Closed? |
| --- | --- | --- |
| [Chore] Refine backlog for Sprint 2 | @anhthu (PO) |  |
| [Chore] Sprint 2 wrap-up | @ngochien (SM) |  |

### Change log


### Result

| Issue | Points | Status | If not done, why |
|-------|--------|--------|------------------|
| #1 |  | TBD | |

**Completed: `<fill in at end of sprint>` points. Velocity this sprint: `<fill in at end of sprint>`**

*Fill this table in with the real status of each issue on the Sunday before
submission - "TBD" and "In progress" for every row is not acceptable for the
milestone (it requires committed, completed, and velocity as actual figures).*

### Retrospective

| Keep doing | Stop doing | Start doing |
|------------|------------|-------------|
| TBD | TBD | TBD |

**One concrete action for next sprint (with an owner):** TBD at Sprint 1 Retro

### Attendance

| Member | Planning | Review | Retro |
|--------|----------|--------|-------|
| @anhthu | Yes | Yes | Yes |
| @nganan | Yes | Yes | Yes |
| @ngochien | Yes | Yes | Yes |
| @thanhlan | Yes | Yes | Yes |
| @tuekhang | Yes | Yes | Yes |