# fix: explain how to recover from an empty quiz publication

Status: [PR #176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176) was merged into `main` on 15 November 2026 and [Issue #172](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172) is closed. Its head branch was `172-h9-recovery`. [PR #171](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/171), containing testing documentation and evidence separately, was also merged.

Closes #172

An empty quiz blocks publishing but the message lacks an explicit next step. Add instructions to open Add Questions, save a question with one correct answer, and publish again. Keep the existing acceptance-criteria text and publication validation.

Files for this PR only: `src/errors.py`, `tests/test_p0_us04_publish.py`.

The isolated change is also available as the [PR #176 patch](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176.patch).

Validation: the regression test failed before the fix; all 8 US04 tests passed after it. The regression checks GET guidance, rejected POST guidance, and unchanged Draft status.

Post-deployment message check: the user supplied a new screenshot in the review conversation showing the empty Draft quiz `business analysis` with the full recovery instruction. This records the user's deployed-site evidence, not a new automated test run. The screenshot is not yet saved in the repository. Existing repository screenshots of the old message remain before-fix evidence. See [live-check.md](../live-check.md) for the scope and provenance of this confirmation.
