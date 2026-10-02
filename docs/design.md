# Milestone 2 — Design Document

## 1. Architecture

## 2. Data model

### ERD

![ERD](images/erd.png)

### Table descriptions

| Table | Purpose | Columns | Constraints / Business rules |
|---|---|---|---|
| `USER` | Stores user accounts for lecturers and students. | `user_id` INT PK, `name` STRING, `email` STRING UNIQUE, `password_hash` STRING, `role` STRING | `user_id` uniquely identifies each user. `email` is unique so one email cannot be used by multiple accounts. `role` distinguishes lecturers from students. |
| `QUIZ` | Stores a lecturer's quiz, its publication state, and the availability and time-limit settings used for student attempts. | `quiz_id` INT PK, `lecturer_id` INT FK, `title` STRING, `status` STRING, `duration_minutes` INT, `start_at` DATETIME, `end_at` DATETIME | `lecturer_id` references `USER.user_id`; it identifies the quiz owner and is used to enforce BR2 (only that lecturer can edit or publish the quiz). A quiz has one owner and may contain many questions and receive many attempts. `status` represents draft, published, or closed state. `duration_minutes` must be positive when set; an attempt must end at the earlier of its duration limit or `end_at` (BR4). Publication requires at least one valid question, with at least two choices and exactly one correct choice per question (BR3). `start_at` and `end_at` define availability. |
| `QUESTION` | Stores the ordered multiple-choice questions that make up a quiz and contribute to its automatically graded score. | `question_id` INT PK, `quiz_id` INT FK, `content` STRING, `points` INT, `position` INT | `quiz_id` references `QUIZ.quiz_id`. Each question belongs to exactly one quiz. `position` determines display order and should be unique within a quiz. Each question needs at least two choices and exactly one correct choice before its quiz can be published (BR3). `points` contributes to the score calculated upon submission. |
| `CHOICE` | Stores the available answer options for a question and identifies the correct option used by automatic grading. | `choice_id` INT PK, `question_id` INT FK, `content` STRING, `is_correct` BOOLEAN | `question_id` references `QUESTION.question_id`. Each choice belongs to one question. A publishable question has at least two choices and exactly one choice with `is_correct = true` (BR3). The correct-answer flag supports grading and review; whether students may see correct answers is controlled by the lecturer's answer-review setting (US09). |
| `ATTEMPT` | Stores a student's quiz session, its submission state and timestamp, and the score calculated from the submitted answers. | `attempt_id` INT PK, `student_id` INT FK, `quiz_id` INT FK, `started_at` DATETIME, `submitted_at` DATETIME, `score` DECIMAL | `student_id` references `USER.user_id` and must identify a student; `quiz_id` references `QUIZ.quiz_id`. Each attempt belongs to one student and one quiz. The attempt starts only when the student is eligible and the quiz is available. `submitted_at` records the single final submission; after submission, answers, score, and event history are immutable through normal application actions (BR6). Enforce at most one submitted attempt per student and quiz (BR5), and reject duplicate submission requests (US12/US13). |
| `ANSWER` | Stores the choice selected for a question in a particular attempt, providing the source data for grading and answer review. | `answer_id` INT PK, `attempt_id` INT FK, `question_id` INT FK, `choice_id` INT FK | `attempt_id` references `ATTEMPT.attempt_id`; `question_id` references `QUESTION.question_id`; `choice_id` references `CHOICE.choice_id` and may be NULL while unanswered. Each answer belongs to one attempt and one question. Enforce at most one answer per `(attempt_id, question_id)` and ensure the selected choice belongs to that question. Submitted answers are immutable as part of BR6. |


## 3. API design

## 4. Walking skeleton

## 5. Design decisions

## 6. What changed since M1
