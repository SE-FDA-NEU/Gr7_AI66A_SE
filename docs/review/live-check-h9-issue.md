# [bug] Empty quiz publication error lacks a recovery instruction

Label: `bug`

Status: [Issue #172](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172) is closed. The dedicated fix, [PR #176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176), was merged into `main` on 15 November 2026. [PR #171](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/171), containing the testing documentation and evidence, was also merged.

URL: https://minilms-nhom7.onrender.com/

Steps: sign in as lecturer → Create Quiz → confirm → leave quiz empty → inspect disabled Publish Quiz and its explanation.

Original actual result (before the fix): `A quiz must contain at least 1 question.` explains the rule but does not tell the user which control to use next.

Expected (H9): explain the blocked publication, minimum question count, and next action: open Add Questions, save a question with one correct answer, then publish again.

Evidence: `docs/images/live-check/mobile/rule-empty-quiz.png`.

Post-fix evidence: the user supplied a new screenshot in the review conversation showing the empty Draft quiz `business analysis` and the full recovery instruction: `Open Add Questions, save a question with one correct answer, then publish again.` The user provided this as a deployed-site check. This confirms the displayed message; it is not a new automated test run. The new screenshot has not been saved as a repository artifact; the existing image above remains historical before-fix evidence.

Acceptance: preserve publication guard and existing required message; show recovery guidance on both the management GET and rejected publication POST; keep quiz Draft.
