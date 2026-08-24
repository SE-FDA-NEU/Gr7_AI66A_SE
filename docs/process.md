## Section 4 — Process Rules the Team Commits To

- Every change reaches `main` through a Pull Request reviewed and approved by at least one other member, with at least one substantive review comment. Self-merging is not allowed, and CI checks, including unit tests and linter checks, must pass before merging.

- Each sprint lasts two weeks. The backlog is re-prioritized at the beginning of each sprint, and no user story enters a sprint without written acceptance criteria.

- Any requirement change made after a sprint has started must be recorded in `docs/changelog.md` before implementation, including the date, requester, and affected user stories.

- Any change to the database schema or the auto-grading algorithm requires an ADR file in `docs/adr/` and approval from at least two team members because these areas may affect stored grades.

- Each sprint ends with a deployable build on the staging environment and a usability testing session with at least two students outside the team. Findings must be added to the backlog within 24 hours.
#### Section 1 — Chosen process and its position on the spectrum

**(a) The model.** We follow **incremental development with throwaway prototyping** used as a technique inside it (prototypes for the quiz-taking screen and for the anti-cheat rules only; prototype code is never merged) [1]. 

One cycle = one two-week iteration and runs as follows. Monday of week 1: the whole team holds iteration planning; the member acting as product owner brings the re-prioritized backlog, and each story entering the sprint must already carry written acceptance criteria [1]. Uncertain UI or scoring stories get a one-day prototype spike first, reviewed by the team before implementation starts [1]. Implementation happens on feature branches, one member per story, with a second member assigned as reviewer at planning time [1]. Every branch reaches main only through a reviewed Pull Request with CI green [1]. Friday of week 2: integration build is deployed to staging, we run a 30-minute usability session with students outside the team, demo the increment, then hold a retrospective [1]. At the end of each cycle, **a potentially deployable, verified, and tested software increment exists on the staging environment**.

**(b) The position.** On the plan-driven ↔ agile spectrum, our process lies at **80% agile and 20% plan-driven**. This hybrid balance is driven by academic project constraints:

*   **Plan-driven elements (Frozen):** The high-level product theme (Mini LMS - D3), the 4 mandatory course Milestones (M1 to M4), and their strict deadlines set by the instructor are frozen for the entire semester [3]. We cannot alter these external milestone gates.
*   **Agile elements (Re-opened every cycle):** The precise user interface of the quiz-taking screen, the prioritization of backlog items, the specific heuristics of anti-cheat rules, and individual test cases are fully re-opened and adapted at the start of each two-week cycle based on user feedback and team velocity [1, 4].
