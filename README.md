# Mini LMS

![CI](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/actions/workflows/ci.yml/badge.svg)

A platform that enables instructors to easily create, manage, and grade quizzes, while providing students with an environment to take assessments, receive results, and view learning statistics.

## Running app: https://minilms-nhom7.onrender.com

> Note: The free hosting plan may sleep when there is no user activity.
> Sample data is reloaded whenever the server restarts.

## Test Accounts

| Role | Email | Password |
|---|---|---|
| Lecturer | ngan.lecturer@example.edu | MiniLMS2026! |
| Lecturer | nam.lecturer@example.edu | MiniLMS2026! |
| Student | duc.student@example.edu | MiniLMS2026! |
| Student | lan.student@example.edu | MiniLMS2026! |
| Student | minh.student@example.edu | MiniLMS2026! |
| Student | an.student@example.edu | MiniLMS2026! |
| TA | mai.ta@example.edu | MiniLMS2026! |

## P0 User Stories

| Story | Starting Point | Navigation |
|---|---|---|
| US01 | `/`, new context | Enter account credentials → Sign in |
| US02 | `/` → Lecturer login | + Create Quiz → Enter title → Create Quiz → Confirm |
| US03 | `/` → Lecturer → Create quiz | Add Questions → Enter question, 4 options, 1 correct answer → Add Question |
| US04 | `/` → Lecturer → Create quiz → Add question | Publish Quiz → Confirm |
| US06 | `/`, new student context | Sign in → Select the newly created quiz → Take quiz → Choose an answer |
| US08 | `/` → Student → Take quiz | Choose an answer → Review & submit → Submit quiz → Confirm |

- **Group:** Group 7 ·
- **Members:** Lê Ngọc Anh Thư, Nguyễn Ngân An, Đào Ngọc Hiền, Nguyễn Thành Lân, Trần Tuệ Khang
- **Product Owner (fixed for the entire term):** Lê Ngọc Anh Thư
- **Scrum Master (rotating each sprint):** Nguyễn Ngân An (Sprint 1) | Đào Ngọc Hiền (Sprint 2) | Trần Tuệ Khang (Sprint 3) | Lê Ngọc Anh Thư (Sprint 4) | Nguyễn Thành Lân (Sprint 5)
- **Board:** https://github.com/orgs/SE-FDA-NEU/projects/17
- **Definition of Done:** [docs/definition-of-done.md](docs/definition-of-done.md)
- **Requirements:** [docs/requirements.md](docs/requirements.md)

## Getting Started

For full setup instructions on a new machine, please refer to: **[docs/SETUP.md](docs/SETUP.md)**