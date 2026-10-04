# Milestone 2 — Design Document

## 1. Architecture

## 2. Data model

### ERD

![ERD](images/erd.png)

### Table descriptions

| Table | Purpose | Columns | Constraints / Business rules |
|---|---|---|---|
| `user` | Stores lecturer, student, and teaching-assistant accounts. | `user_id` INTEGER PK, `name` TEXT, `email` TEXT UNIQUE, `password_hash` TEXT, `role` TEXT | `email` is unique and required. `role` is required and limited to `lecturer`, `student`, or `ta`; application authorization enforces role-based access (BR1). |
| `quiz` | Stores a lecturer's quiz, its publication state, availability, and time limit. | `quiz_id` INTEGER PK, `lecturer_id` INTEGER FK, `title` TEXT, `status` TEXT, `duration_minutes` INTEGER, `start_at` TEXT, `end_at` TEXT | `lecturer_id` references `user.user_id` (BR2). `status` is required, defaults to `draft`, and is limited to `draft`, `published`, or `closed`. Duration must be positive (US11); when both are set, `end_at` must be later than `start_at`. Attempts respect the earlier duration or closing deadline (BR4). Publication validity requirements are enforced by the service (BR3). |
| `question` | Stores ordered multiple-choice questions belonging to a quiz. | `question_id` INTEGER PK, `quiz_id` INTEGER FK, `content` TEXT, `points` INTEGER, `position` INTEGER | `quiz_id` references `quiz.quiz_id`; `points` and `position` must be positive. `(quiz_id, position)` is unique. Quiz publication requires at least one question and at least two choices per question (BR3; checked by application logic). |
| `choice` | Stores answer options and the correctness flag for a question. | `choice_id` INTEGER PK, `question_id` INTEGER FK, `content` TEXT, `is_correct` INTEGER (0/1) | `question_id` references `question.question_id`. A partial unique index permits at most one correct choice per question; publish validation requires exactly one and at least two choices (BR3). |
| `attempt` | Stores a student's quiz session, submission time, and score. | `attempt_id` INTEGER PK, `student_id` INTEGER FK, `quiz_id` INTEGER FK, `started_at` TEXT, `submitted_at` TEXT, `score` REAL | `student_id` references `user.user_id`; `quiz_id` references `quiz.quiz_id`. A partial unique index permits at most one submitted attempt per student and quiz (BR5). Submitted attempts and scores are append-only through normal application actions (BR6). |
| `answer` | Stores the selected choice for each question in an attempt. | `answer_id` INTEGER PK, `attempt_id` INTEGER FK, `question_id` INTEGER FK, `choice_id` INTEGER FK (nullable) | Foreign keys reference `attempt`, `question`, and `choice`; `(attempt_id, question_id)` is unique. A NULL `choice_id` represents an unanswered question. The application must ensure the selected choice belongs to that question and prevent changes after submission (BR6, US13). |


## 3. API design

## 4. Walking skeleton

- Selected route: `GET /student/dashboard`
- Database table: `quiz`, joined with `user` to display the lecturer's name.
- Rows displayed: 12 published quizzes; draft quizzes are excluded.
- Database query executed:

  ```sql
  SELECT
      q.quiz_id,
      q.title,
      u.name AS lecturer_name,
      q.duration_minutes,
      q.end_at
  FROM quiz q
  JOIN user u ON u.user_id = q.lecturer_id
  WHERE q.status = 'published'
  ORDER BY q.end_at ASC;
  ```

- Runtime proof:

  ![Student dashboard showing 12 published quizzes](images/skeleton.png)

- Setup instructions: See [docs/SETUP.md](SETUP.md).

## 5. Design decisions

## 6. What changed since M1
