# Operations

**Document:** Operations · Version 1.0 · 2026-11-15

## 1 How to run and release

Live app: [minilms-nhom7.onrender.com](https://minilms-nhom7.onrender.com), a Render Python web service on the Free plan, deployed from `main`. Merge a reviewed PR to `main`; after CI passes, Render automatically deploys. Confirm the deploy is Live and check `/health`.

To roll back a merged change, create a branch from `main`, run `git revert -m 1 <merge-commit>` for the merge commit, open a PR, wait for green CI, then merge it; Render deploys the reverted version automatically.

Issue [#158](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/158) records PR #169 merged at 15:40 and Render showing Live at 15:41 (about 1 minute). A later observation tracked PR [#170](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/170) creation to Render Live on 2026-11-13 (Friday): t1 was 19:15:53 UTC+07 (Asia/Ho_Chi_Minh), when the PR was created; t2 was 19:20 UTC+07, when Render showed Live (minute precision). Elapsed time was about 5 minutes. This measures PR-creation-to-Live, not merge-to-Live, and was not a Thursday trial.

![Render Events showing PR #170 Live on 2026-11-13 at 19:20](images/deploy-pr-170-render-live.jpg)

## 2 The CI pipeline

The workflow runs on pushes and PRs targeting `main` or `develop`.

| Step | What it checks or does |
|---|---|
| Checkout repository | Checks out the commit being tested. |
| Set up Python | Installs Python 3.11 and enables pip dependency caching. |
| Install dependencies | Upgrades pip and installs `requirements.txt`. |
| Run tests with pytest | Runs `pytest --cov=src tests/` with the repository on `PYTHONPATH`; collects coverage for `src`. |

Latest successful run on `main`: [CI Pipeline #43700445212](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/actions/runs/43700445212), **1m 09s** in Actions.

![Branch protection settings](images/branch-protection.png)

## 3 Monitoring

Each request writes a JSON log to stdout with method, route-template path, status code, and duration in milliseconds. Server exceptions log filtered stack-frame locations, not exception messages. Read these entries in Render → Logs. The app does not log passwords, email addresses, quiz answers, request bodies, cookies, or raw URLs.

`/health` opens SQLite read-only and queries the `user` table. It returns 200 when the query succeeds and 503 when the database is unavailable; it does not check every application feature.

Track the **5xx error rate** (5xx responses divided by all requests) and **response time** (`duration_ms`, summarized as p95) from request logs. Treat a sustained rise in either versus its recent baseline as deterioration; no numeric alert threshold is configured. The Render Free plan provides only basic Render notifications; this app has no custom alerting.

Issue [#159](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/159) is closed but contains no execution results. This guide describes the live health and monitoring checks; it does not claim that the issue's six-story live smoke test was completed.

## 4 Risks

Each risk below comes from something in the repository. No open issue covers them, so each plan is "accepted" with the reason.

| Item | Layer | What could happen | Plan |
|---|---|---|---|
| SQLite reseed on Render ([ADR 0003](adr/0003-hosting-sqlite-reseed.md)) | Hosting / data | Every restart or redeploy wipes the disk; quizzes, attempts and lockouts created on the live URL are lost. | Accepted: the live server is a demo with no real users; ADR 0003 lists when to move to PostgreSQL or a persistent disk. |
| Seed quiz deadlines (`data/seed_quizzes.csv`) | Seed data | Every seeded quiz has `end_at` on or before 2026-11-01, so after a reseed no seeded quiz can be taken. | Accepted: the demo script in [live-check.md](live-check.md) always creates and publishes a fresh quiz. |
| Tests that depend on today's date | Tests | Tests build their database from the same seed; a test that uses a seeded deadline without fixing the clock fails once that date passes, as the publish test did from 2026-10-31 (commit `bacabb6`). | Accepted: existing time-sensitive tests patch `utc_now_naive`; reviewers check new tests for the same. |
| BR3 allows 2+ choices, the form requires exactly 4 (`CHOICE_COUNT` in `question_service.py`) | Service / requirements | A lecturer cannot create a 2- or 3-choice question; the requirement and the code disagree. | Accepted: recorded as a known deviation in [testing.md](testing.md) §1; US03 boundary tests pin 3 (refused) and 4 (accepted). |
| No automated interface tests | Interface | A template or JavaScript regression passes CI and reaches Render; `docs/live_probe.py` runs by hand and is not in CI. | Accepted: the interface is checked by manual live checks, which is how H9 ([#172](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172)) was found. |
| Unpinned dependencies (`Flask>=3.0.0`, `gunicorn>=22.0`) | Build / deploy | A new major release changes behaviour without any code change. | Accepted: versions are not pinned yet; CI is where a failure would be noticed first. |

## 5 Maintenance

| Area | What to do | Who | How often |
|---|---|---|---|
| Backlog and requirements | Triage bugs from live checks; keep BR3 and `traceability.md` in sync with `requirements.md` | Thư (PO) | Every backlog refinement |
| Deploy and release | After each merge, confirm Render shows Live and `/health` returns 200; tag releases (#163) | Lân (SM) | Every merge to `main` |
| Monitoring | Review 5xx rate and p95 `duration_ms` in Render → Logs | An | Weekly, and after each deploy |
| Database and seed data | Move seed quiz deadlines forward, check demo accounts, re-read ADR 0003's "what would change this decision" | Hiền | Before every demo |
| Dependencies | Install `requirements.txt` on a clean clone and run `python -m pytest -v` | Khang | Monthly |
| Operations docs | Keep `SETUP.md` and sections 1–3 of this file matching the live setup | Khang | When the deploy or CI changes |

## 6 Lessons learned

**1. A test failed because the calendar moved.** *What happened:* the publish test started failing on 2026-10-31 because seeded quiz 13 had a deadline of 2026-10-30 (Sprint 4 log). *What we changed:* commit `bacabb6` clears that quiz's `end_at` inside the test. *Next time:* tests never rely on seed dates; they set their own dates or patch the clock.

**2. Render's disk is wiped on restart.** *What happened:* on the free plan, `data/minilms.db` disappears on every restart and redeploy, and running `init_db()` at start-up would drop all tables. *What we changed:* ADR 0003 adds `ensure_database()`, which seeds only when the file or `user` table is missing; tests ED01–ED03 protect existing data. *Next time:* check the host's storage rules when choosing the database, not after deploying.

**3. The P0 tests missed an unhelpful error message.** *What happened:* a manual click-through on the live URL found H9: the empty-quiz publish error explains why but not how to recover ([#172](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172), severity Blocker). The automated US04-03 test only checked that publishing was refused. *What we changed:* PR [#176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176) adds the recovery step and extends US04-03 to check it. *Next time:* run a live click-through early in the sprint and include the recovery step in the expected result for every error case.

**To confirm with the team**

- Whether the Sprint 4 retrospective adopted "fix the clock in tests" as its action; `sprint-log.md` still shows a placeholder.
- Whether PR #176 is merged and the H9 fix is running on Render; `live-check.md` says it was not yet deployed.
- Whether PR #169 and its revert, PR #170, were a deliberate rollback rehearsal.
