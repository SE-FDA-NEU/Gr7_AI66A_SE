## Section 3 — Risks of the opposite choice

If we had gone fully plan-driven (Waterfall with a complete SRS signed off before construction), the single biggest risk is specifying the analytics and anti-cheat modules before any real attempt data exists.

Mechanism: those requirements are discoverable only by observing actual student attempts — which question wording produces guessing, what a score distribution looks like with 30 students rather than 3. A frozen SRS forces us to implement guessed statistics. The mismatch is invisible until integration and system testing, which in Waterfall sit at the end of the schedule where there is no slack. Every discovery then becomes a formal change request, and rework competes with the fixed demo date.

First observable symptom: at Milestone 3, the first end-to-end run with real attempt data, the score-distribution screen answers a question no instructor actually asks, and the list of pending change requests starts growing faster than we close them — while the coding phase is officially "complete".