# fix: explain how to recover from an empty quiz publication

Status: submitted as [PR #176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176) for [Issue #172](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172). The PR is open and not merged; its head branch is `172-h9-recovery`, targeting `main`. PR #171 retains testing documentation and evidence separately.

Closes #172

An empty quiz blocks publishing but the message lacks an explicit next step. Add instructions to open Add Questions, save a question with one correct answer, and publish again. Keep the existing acceptance-criteria text and publication validation.

Files for this PR only: `src/errors.py`, `tests/test_p0_us04_publish.py`.

The isolated change is also available as [live-check-h9.patch](live-check-h9.patch).

Validation: the regression test failed before the fix; all 8 US04 tests passed after it. The regression checks GET guidance, rejected POST guidance, and unchanged Draft status.

Deployment validation remains pending. Existing Render screenshots show the previous message.
