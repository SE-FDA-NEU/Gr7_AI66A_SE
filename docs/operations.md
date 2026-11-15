# Operations

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
