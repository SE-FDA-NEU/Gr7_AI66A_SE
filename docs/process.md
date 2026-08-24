## Section 2 — The five diagnostic questions

**1. Are your requirements stable or volatile?**
Mixed, and this is the main driver of our choice. The transactional core (create quiz, take quiz, auto-grade) is highly stable; our evidence is that the entity list in our first design sketch perfectly matches the current schema. However, the analytics and anti-cheat modules are volatile. For instance, our definition of a "difficult question" changed twice in three weeks (from "under 50% correct" to a discrimination index) after consulting an instructor. We cannot definitively specify statistics until we analyze real attempt data.

**2. Does the project carry safety or legal impact?**
No safety criticality, but it does carry academic integrity constraints. Because the system stores grades (academic records), privacy and data integrity matter. We adopt proportionate formality rather than heavy bureaucracy: the exam attempt table is append-only to maintain a reliable audit log. Furthermore, any change to the auto-grading algorithm or core database schema requires a lightweight Architecture Decision Record (ADR) and two peer approvals.

**3. Is your team large and distributed, or small and co-located?**
We are four members, co-located on the same campus, with two scheduled face-to-face sessions per week plus an active Discord channel. Communication cost is extremely low, allowing verbal coordination and shared Kanban boards to replace heavy specification documents. Our primary risk is bus factor; therefore, mandatory PR reviews are enforced not just to catch defects, but to actively spread system knowledge across the team.

**4. Can your customer engage continuously, or only at fixed checkpoints?**
Engagement is two-tier. The instructor (the authoritative customer) is available formally only at the four fixed milestones and weekly labs. Meanwhile, real users (classmates) are recruited every sprint for continuous usability testing. This asymmetry—continuous proxy feedback bounded by rigid authoritative gates—is exactly why our process must be a hybrid rather than fully agile.

**5. What do organizational culture and contract constraints allow?**
The course establishes four strict milestones and a final demo date that cannot be moved. With time fixed and team capacity constrained, scope is our only variable. This constraint mandates a strictly prioritized backlog and an "always-shippable" increment approach. Whatever exists on the demo date must be a coherent, functioning subset of the Mini LMS, rather than a half-finished whole.
