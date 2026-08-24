## Section 4 — Process Rules the Team Commits To

- Every change reaches `main` through a Pull Request reviewed and approved by at least one other member, with at least one substantive review comment. Self-merging is not allowed, and CI checks, including unit tests and linter checks, must pass before merging.

- Each sprint lasts two weeks. The backlog is re-prioritized at the beginning of each sprint, and no user story enters a sprint without written acceptance criteria.

- Any requirement change made after a sprint has started must be recorded in `docs/changelog.md` before implementation, including the date, requester, and affected user stories.

- Any change to the database schema or the auto-grading algorithm requires an ADR file in `docs/adr/` and approval from at least two team members because these areas may affect stored grades.

- Each sprint ends with a deployable build on the staging environment and a usability testing session with at least two students outside the team. Findings must be added to the backlog within 24 hours.
