# Mini LMS: Testing (Milestone 4)

**Team 07 · Group 7 · Sprint 4**
**Repository:** https://github.com/SE-FDA-NEU/Gr7_AI66A_SE


> **How to read this document.** Section 2 lists every test case of every P0 story (US01, US02, US03, US04, US06, US08). Each test case ID, for example `US02-03`, appears in the name or in a comment of exactly one pytest test in `tests/`. Section 3 shows how to run them all with one command. Section 4 records what the tests found.

---

## 1. What we test, and why

| Layer | Location | What kind of test it gets | Why |
|---|---|---|---|
| Services | `src/services/` | Unit tests with pytest, using a temporary SQLite database | All business rules live here (quiz validation, publish rules, attempt timing, scoring); a mistake here costs the most |
| Repository | `src/repositories/`, `src/db.py` | Integration tests on a temporary SQLite file (`tmp_path`) | Checks the SQL, the database constraints and that data is stored and updated correctly |
| Routes | `src/routes/` | Flask test client, no running server | Checks status codes, redirects, role-based access (BR1, BR2) and the messages shown to the user |
| Interface | `src/templates/`, `src/static/` | None automated | `<reason: for example, checked by hand with real users in Milestone 3; layout changes too often for automated tests>` |

**Risk.** `<2–3 sentences.>` Suggested content: we tested most the parts where a mistake changes a student's result or exposes data, namely sign-in and role checks (US01), the attempt timer and deadline (US06), and submission and scoring (US08), because an error there directly affects grades and access. Publishing rules (US04) were tested next, since a quiz published without valid questions cannot be taken correctly. The interface was tested least because it only presents what the services already decide.

**Known deviation from the requirements.** BR3 says a question needs at least 2 choices, but the question form always requires exactly 4 filled choices (`CHOICE_COUNT = 4` in `question_service.py`). The US03 boundary tests therefore use 3 filled choices (refused) and 4 filled choices (accepted).

---

## 2. Test cases for every P0 story

**Kind** is one of: `normal`, `error`, `boundary, just below`, `boundary, on the limit`, `boundary, just above`.
Every P0 story has at least three test cases: one normal case, one error case, and, where the rule contains a number, boundary cases on both sides of it.

### 2.1 US01: Sign in and receive the correct role

| ID | Story | Input | Expected result | Kind |
|---|---|---|---|---|
| US01-01 | US01 Sign in | Lecturer enters a valid email and password | Redirect to `/lecturer/dashboard` | normal |
| US01-02 | US01 Sign in | Student enters a valid email and password | Redirect to `/student/dashboard` | normal |
| US01-03 | US01 Sign in | Valid email, wrong password (1st failure) | 401, friendly error message, account not locked | error |
| US01-04 | US01 Sign in | 4 wrong passwords within 10 minutes, then the correct password | Sign-in succeeds | boundary, just below |
| US01-05 | US01 Sign in | 5th wrong password within 10 minutes | Account locked; message "Too many failed attempts. Try again in 15 minutes." | boundary, on the limit |
| US01-06 | US01 Sign in | 4 recent wrong passwords plus 1 older than 10 minutes | Account not locked (old failure is outside the window) | boundary, just above |
| US01-07 | US01 Sign in | Locked account tries again at 14:59 and at 15:01 after locking | At 14:59 still blocked; at 15:01 sign-in allowed | boundary, both sides |
| US01-08 | US01 Sign in | Student opens `/quiz/create`; guest opens `/student/dashboard` | 403 for the student; guest redirected to `/login` (BR1) | error |
| US01-09 | US01 Sign in | Lecturer edits a quiz owned by another lecturer | Rejected: "You do not have permission to edit this quiz." (BR2) | error |

### 2.2 US02: Lecturer creates a quiz

| ID | Story | Input | Expected result | Kind |
|---|---|---|---|---|
| US02-01 | US02 Create quiz | Title "Midterm Quiz 1", description "Week 5 review" | Quiz created with status Draft | normal |
| US02-02 | US02 Create quiz | Duration 30 minutes | Duration stored as 30 | normal |
| US02-03 | US02 Create quiz | Empty title | Rejected: "Quiz title is required."; no quiz created | error |
| US02-04 | US02 Create quiz | Title with only spaces | Rejected, same as US02-03 | error |
| US02-05 | US02 Create quiz | Duration 0 | Rejected; no quiz created | boundary, just below |
| US02-06 | US02 Create quiz | Duration 1 | Accepted; stored as 1 | boundary, on the limit |
| US02-07 | US02 Create quiz | Duration -1 | Rejected | error |
| US02-08 | US02 Create quiz | Student submits the create-quiz form | 403; no quiz created | error |

### 2.3 US03: Lecturer adds multiple-choice questions

| ID | Story | Input | Expected result | Kind |
|---|---|---|---|---|
| US03-01 | US03 Add questions | Quiz with 0 questions, add 1 valid question | Question count becomes 1 | normal |
| US03-02 | US03 Add questions | Question with 4 choices and 1 correct answer | Exactly 4 choices and 1 correct answer stored | normal |
| US03-03 | US03 Add questions | No correct answer selected | Rejected: "Please select one correct option."; nothing saved | error |
| US03-04 | US03 Add questions | Only 3 of the 4 choices filled in | Rejected; nothing saved | boundary, just below |
| US03-05 | US03 Add questions | All 4 choices filled in | Accepted | boundary, on the limit |
| US03-06 | US03 Add questions | Points = 0 | Rejected | boundary, just below |
| US03-07 | US03 Add questions | Points = 1; another lecturer adds a question to the quiz | 1 accepted; other lecturer gets 403 | boundary, on the limit + error |

### 2.4 US04: Lecturer publishes a quiz

| ID | Story | Input | Expected result | Kind |
|---|---|---|---|---|
| US04-01 | US04 Publish | Owner publishes a quiz with 10 valid questions | Status becomes published | normal |
| US04-02 | US04 Publish | Quiz with exactly 1 valid question | Publish succeeds | boundary, on the limit |
| US04-03 | US04 Publish | Quiz with 0 questions | Rejected: "A quiz must contain at least 1 question."; status stays draft | boundary, just below |
| US04-04 | US04 Publish | Quiz with a question that has 0 correct choices | Rejected (BR3); status stays draft | error |
| US04-05 | US04 Publish | Quiz is closed; student tries to start it | Rejected; no attempt created | error |
| US04-06 | US04 Publish | Published quiz with 1 submitted attempt; lecturer closes it | Status closed; submitted attempt still accessible | normal |
| US04-07 | US04 Publish | Another lecturer publishes the quiz | 403; quiz unchanged (BR2) | error |
| US04-08 | US04 Publish | Publish a quiz that is already published | 409 | error |

### 2.5 US06: Student starts a quiz attempt

| ID | Story | Input | Expected result | Kind |
|---|---|---|---|---|
| US06-01 | US06 Start attempt | Student starts a published quiz of 10 questions | Question 1 shown; questions displayed one at a time | normal |
| US06-02 | US06 Start attempt | Quiz with a 30-minute limit, attempt just started | Timer starts at 30:00 (1800 s) | normal |
| US06-03 | US06 Start attempt | Select B on question 3, move away and come back | B is still selected | normal |
| US06-04 | US06 Start attempt | Refresh the page mid-attempt | Same question and same remaining time restored | normal |
| US06-05 | US06 Start attempt | Quiz of 10 questions: open question 0, 1, 10, 11 | 0 and 11 return 404; 1 and 10 open | boundary, both sides |
| US06-06 | US06 Start attempt | Access the attempt at 29:59, 30:00 and 30:01 after the start | 29:59 still open; 30:00 auto-submitted; 30:01 cannot continue | boundary, three points |
| US06-07 | US06 Start attempt | Start a draft quiz, then a closed quiz | Rejected; no attempt created | error |
| US06-08 | US06 Start attempt | Attempt limit is 2: start a 2nd and a 3rd attempt | 2nd allowed; 3rd rejected (BR5) | boundary, both sides |

### 2.6 US08: Student submits a quiz

| ID | Story | Input | Expected result | Kind |
|---|---|---|---|---|
| US08-01 | US08 Submit | All 10 questions answered, student confirms | Status Submitted; exactly 1 submission timestamp stored | normal |
| US08-02 | US08 Submit | Question 7 unanswered, student requests submission | "Question 7" listed; explicit confirmation required; not yet submitted | error |
| US08-03 | US08 Submit | Question 7 unanswered, student confirms | Submitted; question 7 scores 0 | normal |
| US08-04 | US08 Submit | Submit the same attempt a second time | Rejected; score and answers unchanged | error |
| US08-05 | US08 Submit | Change an answer after submission | Rejected (BR6) | error |
| US08-06 | US08 Submit | Time limit 30 minutes: submit at 29:59 and at 30:01 | 29:59 submitted normally; at 30:01 the attempt was already auto-submitted and the late answer is not saved | boundary, both sides |
| US08-07 | US08 Submit | A different student submits this attempt | Rejected; attempt unchanged | error |

### Appendix: P1 stories (extra coverage, not required for P0)

`<Move the existing US09, US10 and US11 tables here unchanged.>`

---

## 3. Automated tests

**Where.** All tests are in `tests/`. Every test case in Section 2 is a pytest test, with its ID in the test name (for example `test_us02_05_duration_0_is_rejected`) or in a comment (`# US02-05`).

| Story | Test file |
|---|---|
| US01 | `tests/test_p0_us01_login.py` |
| US02 | `tests/test_p0_us02_create_quiz.py` |
| US03 | `tests/test_p0_us03_questions.py` |
| US04 | `tests/test_p0_us04_publish.py` |
| US06 | `tests/test_p0_us06_start_attempt.py` |
| US08 | `tests/test_p0_us08_submit.py` |

**No server and no real database.** The tests use the Flask test client and a temporary SQLite file created in pytest's `tmp_path` by `init_db`. They never read `data/minilms.db` and do not depend on today's date.

**One command runs them all** (from the repository root, after the setup steps in `docs/SETUP.md`):

```bash
python -m pytest -v
```

**Output** (clean clone, `<date>`):

![(SM thêm ảnh vào đây) Full output of python -m pytest -v](images/testing/pytest-output.png)

`<N> passed in <T> s` (SM thay số)

---

## 4. What the tests found

### Entry 1: `<short title>`

`<Choose ONE of the two options below and delete the other.>`

**Option A: a bug found by the tests**

- **Issue:** `<#number and one sentence: what was wrong>`
- **Fix:** `<PR #number and what changed>`
- **Test that now guards it:** `<test_name> (<test case ID>)`

**Option B: a rule broken on purpose**

- **Rule broken:** `<for example: in src/services/quiz_service.py, changed "if len(questions) < 1" to "< 0">`
- **Test that went red:** `<test_name> (<test case ID>)`
- **Red output:**

  ![Failing test output after the deliberate change](images/testing/mutation-red.png)

- **Reverted:** the code was restored and the same test passes again (`<N> passed`).