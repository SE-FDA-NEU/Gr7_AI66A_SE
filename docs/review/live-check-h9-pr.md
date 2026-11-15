# fix: explain how to recover from an empty quiz publication

Status: prepared locally; no GitHub PR has been created. Submit this fix separately from live-check evidence. Attach the actual bug issue number when available.

An empty quiz blocks publishing but the message lacks an explicit next step. Add instructions to open Add Questions, save a question with one correct answer, and publish again. Keep the existing acceptance-criteria text and publication validation.

Files for this PR only: `src/errors.py`, `tests/test_p0_us04_publish.py`.

The isolated change is also available as [live-check-h9.patch](live-check-h9.patch).

Validation: the regression test failed before the fix; all 8 US04 tests passed after it. The regression checks GET guidance, rejected POST guidance, and unchanged Draft status.

Deployment validation remains pending. Existing Render screenshots show the previous message.
