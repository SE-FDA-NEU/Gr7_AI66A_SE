# [bug] Empty quiz publication error lacks a recovery instruction

Label: `bug`

Status: tracked in [Issue #172](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172), labelled `bug`. The dedicated fix is [PR #176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176), currently open and not merged.

URL: https://minilms-nhom7.onrender.com/

Steps: sign in as lecturer → Create Quiz → confirm → leave quiz empty → inspect disabled Publish Quiz and its explanation.

Actual: `A quiz must contain at least 1 question.` explains the rule but does not tell the user which control to use next.

Expected (H9): explain the blocked publication, minimum question count, and next action: open Add Questions, save a question with one correct answer, then publish again.

Evidence: `docs/images/live-check/mobile/rule-empty-quiz.png`.

Acceptance: preserve publication guard and existing required message; show recovery guidance on both the management GET and rejected publication POST; keep quiz Draft.
