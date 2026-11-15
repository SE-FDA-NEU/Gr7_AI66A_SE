# P0 live check — 15 November 2026

Single starting URL: **https://minilms-nhom7.onrender.com/**. Supplied lecturer URL: https://minilms-nhom7.onrender.com/lecturer/dashboard.

Automated method: **automated browser-based functional testing** with Playwright and headless Chrome, using fresh contexts without shared cookies (equivalent to private sessions), a 1365×900 desktop viewport, and a 390×844 touch-enabled mobile viewport. Seeded demo accounts from `SETUP.md` signed in successfully. The script uses `goto` only for the homepage, then clicks links, buttons, and confirmations; it does not enter subpage URLs. Reload checks represent F5. The physical-phone checks are **manual mobile testing** reported by Nguyễn Ngân An with eight original screenshots, recorded separately from the independent reviewers' entries below.

## Story results

| Story | Starting point | Click path | Result | Screenshots |
| --- | --- | --- | --- | --- |
| US01 | `/`, fresh context | Enter credentials → Sign in | PASS: lecturer and student reach their role-specific dashboard | [Lecturer](images/live-check/mobile/US01-lecturer.png), [student](images/live-check/mobile/US01-student-mobile.png) |
| US02 | `/` → lecturer sign-in | + Create Quiz → enter title → Create Quiz → confirm | PASS: Draft created and retained after reload | [Created](images/live-check/mobile/US02-created.png), [F5](images/live-check/mobile/US02-after-F5.png) |
| US03 | `/` → lecturer → create quiz | Add Questions → enter a question, four choices, one correct answer → Add Question | PASS: one question saved | [Question added](images/live-check/mobile/US03-added.png) |
| US04 | `/` → lecturer → create quiz → add question | Publish Quiz → confirm | PASS: Published; available on the student dashboard | [Published](images/live-check/mobile/US04-published.png) |
| US06 | `/`, fresh student context | Sign in → find the new quiz → Take quiz → select an answer | PASS: question and timer visible; radio option selectable at 390×844 | [Taking the quiz](images/live-check/mobile/US06-mobile-answer.png) |
| US08 | `/` → student → Take quiz | Select answer → Review & submit → Submit quiz → confirm | PASS: Quiz submitted, score 1/1 (100%), submission time shown | [Submitted](images/live-check/mobile/US08-mobile-submitted.png) |

Complete mobile run: quiz **18**, titled `LIVE CHECK 20261115-150924`. These quizzes are real test data, not fabricated screenshot content. Earlier trials may have left separate drafts; other users' data and submissions were not deleted. Destination log: [mobile/results.json](images/live-check/mobile/results.json). Desktop screenshots and logs are stored separately in `images/live-check/desktop/`.

**All 6/6 main story flows were reachable by clicking on the deployed site in the automated browser.** Physical-phone results supplied by An and independent reviewer entries are included below. PR #171 and PR #176 have been merged. A newer user-supplied screenshot shows the corrected H9 guidance; its provenance and verification scope are recorded below. Cross-checking against the actual M3 feedback sheet remains pending.

## Create data, then reload

Create a separate quiz → confirm → capture Draft state → reload → verify the same title remains. The US02 before/after F5 screenshots are linked above. This confirms persistence across page reload, not across a Render restart or redeploy. See `adr/0003-hosting-sqlite-reseed.md` for the SQLite hosting decision.

## Three business rules prepared for deliberate violations

| Rule | Steps from the homepage | Result and H9 assessment |
| --- | --- | --- |
| Quiz with zero questions | Lecturer → Create Quiz → confirm → leave it without questions → inspect Publish Quiz | Original check: publishing disabled and `A quiz must contain at least 1 question.` shown, but recovery guidance missing. [Before-fix screenshot](images/live-check/mobile/rule-empty-quiz.png). After PR #176, a newer screenshot supplied in the conversation includes `Open Add Questions, save a question with one correct answer, then publish again.` See the H9 confirmation below. |
| Start a quiz that has just closed | Student opens the dashboard showing a Published quiz; lecturer closes it in a separate session; student clicks Take/Retake without refreshing | Blocked: `This quiz is closed, so you can't start it. Contact your lecturer if you need access.` This explains what happened, why, and what to do next. [Screenshot](images/live-check/mobile/rule-closed-quiz.png). |
| Fifth incorrect password | Fresh session → secondary demo account `minh.student@example.edu` → incorrect password five times | PASS: `Too many failed attempts. Try again in 15 minutes.` [Fifth-attempt screenshot](images/live-check/desktop/rule-fifth-wrong-password.png). The account is temporarily locked for 15 minutes; do not use it for the main demo. |

The original automated live check did not test duplicate submission. The three scenarios above were selected for the demo; duplicate-submission protection is covered by existing US08 tests.

## Bug and fix

| Bug | Issue | Fix | Test | Status |
| --- | --- | --- | --- | --- |
| H9: empty-quiz error lacks recovery guidance | [Issue #172 — bug, closed](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172) | [PR #176 — merged](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176): update `src/errors.py` to explain opening Add Questions, saving a question with a correct answer, and publishing again | `test_us04_03_quiz_with_0_questions_cannot_be_published`: checks rejected POST and management GET; failed before the fix and passed afterward | PR #176 contains only two code/test files; PR #171 contains documentation and evidence. Both merged on 15 November 2026. A user-supplied post-fix screenshot shows the guidance; see the scope below. [Details](review/live-check-h9-pr.md) |

### Post-fix H9 message confirmation

The user supplied a newer screenshot in the conversation as a deployed Render-site check: quiz **`business analysis`**, **Draft**, **0 questions**, 30 minutes, one attempt per student. The message explains why publication is blocked and includes the full instruction: **`Open Add Questions, save a question with one correct answer, then publish again.`** Draft is the expected state for a newly created, unpublished quiz.

This confirms the displayed message based on the user's screenshot. It is not a new automated test run or a fresh verification of the entire publication flow. The newer screenshot is not saved as a repository file, so no post-fix image link is available yet. The older phone screenshots are not evidence of the new message; they remain unchanged as before-fix evidence.

No dead ends or steps requiring a manually entered subpage URL were found in the tested flows. Script selector mistakes and environment permissions for temporary test directories are not counted as product bugs.

Historical local verification: the baseline suite had **273 passed** (538.56 seconds); that run started before the message change. After the fix, `tests/test_p0_us04_publish.py` had **8 passed** (27.86 seconds). The empty-quiz regression test failed before the fix. `git diff --check`, script syntax checks, and evidence-link checks passed. These are historical results, not a new test run. CI for [PR #171](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/171) and [PR #176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176) was green when checked before this documentation update; consult GitHub for checks on any newer commit.

## Two changes following M3

Commit [47805a1](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/commit/47805a14d4835b9032807f16ace1adb0a8abd197), dated **24 October 2026, 13:36 UTC+7**, referencing #108, describes the four changes mentioned in the task. The selected changes are **question editing** and **configurable attempt limits**. The script edited a question, changed the limit from one to two attempts, and verified that it remained two after reloading on Render.

| Change | Before | After on the deployed site |
| --- | --- | --- |
| Edit questions | [US03 wireframe, 18 October](images/m3-fixes/edit-question-before.png) | [Edited content and editing control](images/m3-fixes/edit-question-after.png) |
| Configure attempt limits | [US04 wireframe, 18 October](images/m3-fixes/attempt-limit-before.png) | [Maximum attempts = 2 after saving and reloading](images/m3-fixes/attempt-limit-after.png) |

**Evidence limitation:** before images are existing repository wireframes, not screenshots of the M3 product. They illustrate the earlier design but do not independently prove that the features were absent. The lecturer's actual M3 feedback sheet has not been provided, so these changes cannot yet be matched against individual comments. Obtain and cross-check the sheet before signing off the M3 requirement. Image provenance and commits are recorded in [m3-fixes/README.md](images/m3-fixes/README.md).

## Five-minute demo script

1. 0:00–0:30: open `/` in a private session and sign in as a lecturer.
2. 0:30–1:15: create a quiz labelled DEMO; reload to show persistence; point out the message blocking publication of a zero-question quiz.
3. 1:15–2:15: add one question, four choices, and one correct answer; publish and confirm.
4. 2:15–3:45: open `/` in a separate phone session, sign in as a student, and click Take quiz; show the timer, select an answer, review, submit, and show the score.
5. 3:45–4:30: present both before/after pairs, the 24 October commit, and the M3 feedback sheet when available.
6. 4:30–5:00: violate a rule selected by the lecturer. Use a secondary demo account for lockout; for the closed-quiz scenario, prepare an unrefreshed student dashboard and a lecturer session.

## Physical-phone check — Nguyễn Ngân An

Date: **15 November 2026**. Device: **iPhone 14 Pro**. Browser: **Safari**, as reported by the tester. Screenshot times range from **16:41 to 16:49**; the submission result explicitly shows **16:49 UTC+7**. The tester reported completing quiz creation, reload, attempted publication without questions, question creation, publication, student sign-in, taking the quiz, and submission. No unexpected errors were reported; expected validation messages appeared.

The actual quiz title is **`iphone 14 pro + safari`**, rather than the suggested `PHONE REVIEW`. Images were copied unchanged from the supplied files, not recreated or edited.

| Check | Tester-reported result | Evidence and limitations |
| --- | --- | --- |
| US01 — sign-in and role switch | PASS: lecturer sign-in, sign-out, then student sign-in | [Student dashboard](images/live-check/iphone-14-pro-safari/01-student-dashboard.jpg); management screenshots show lecturer access, but no separate sign-in screenshot was supplied |
| US02 — create quiz and reload | PASS: a 30-minute quiz was created and remained after reload | [New Draft quiz with zero questions](images/live-check/iphone-14-pro-safari/03-created-empty-quiz.jpg). Persistence is confirmed by the tester's report; no separate before/after reload pair was supplied |
| US03 — add a question | PASS: added `1+1`, four choices, and one correct answer | [Validation when no correct answer is selected](images/live-check/iphone-14-pro-safari/05-required-correct-choice.jpg); the question also appears on the taking screen |
| US04 — publish | PASS: published the quiz and it became available to the student | [Enabled Publish button](images/live-check/iphone-14-pro-safari/06-publish-enabled.jpg), [quiz on the student dashboard](images/live-check/iphone-14-pro-safari/01-student-dashboard.jpg); an enabled button alone is not confirmation of Published status |
| US06 — start and select an answer | PASS: timer visible and an answer selectable | [Taking screen, timer 29:54](images/live-check/iphone-14-pro-safari/07-take-quiz-timer.jpg). The image precedes radio selection; selection is supported by the tester's report and graded result |
| US08 — submit | PASS: reviewed, confirmed submission, and received a score | [Quiz submitted, 1/1 (100%), 16:49 UTC+7](images/live-check/iphone-14-pro-safari/08-submitted-result.jpg) |
| BR3 — block publication with zero questions | PASS for preventing publication: Publish disabled and minimum-question message shown | [Disabled button and explanation — before the H9 fix](images/live-check/iphone-14-pro-safari/04-empty-quiz-publish-blocked.jpg). This phone run still lacked recovery guidance. The newer message is recorded separately in the post-fix H9 section; older results and images are unchanged |
| Additional validation | Empty question text and missing correct-answer selection blocked | [Required question field](images/live-check/iphone-14-pro-safari/02-required-question.jpg), [required correct-answer selection](images/live-check/iphone-14-pro-safari/05-required-correct-choice.jpg); these are native browser validation messages |

These are **physical-phone checks performed by An**, not checks performed by the assistant. An's results are recorded separately from other reviewers' entries below.

## Independent reviewers — reviewer-supplied results

These entries are **manual mobile testing** supplied by the reviewers. Requirement: use their own phone independently of An's results, enter only the homepage URL, repeat at least two stories, and violate one business rule. Supplied results and screenshots are preserved below.

| Reviewer | Time, UTC+7 | Device/browser | Story 1: result/evidence | Story 2: result/evidence | Business rule: result/evidence |
| --- | --- | --- | --- | --- | --- |
| Le Ngoc Anh Thu | 16:56 | Honor X6C - Chrome | [US04](images/live-check/reviewer/thu-01-student-dashboard.png) | [US08](images/live-check/reviewer/thu-03-submitted.png) | [BR3 - A quiz cannot be published unless it contains at least 1 question](images/live-check/reviewer/thu-04-empty-quiz-rule.png) |
| Nguyen Thanh Lan | 17:05 | Honor X7C - Chrome | [US06](images/live-check/reviewer/lan-02-take-timer.png) | [US01](images/live-check/reviewer/lan-06-too-many-login-item.png) | [BR5 - Each student may submit up to the quiz&#39;s configured attempt limit](images/live-check/reviewer/lan-05-double-submit.png) |

## Rerun the automated checks

Install Playwright in the test environment (`python -m pip install playwright`); the script uses the Windows Chrome path specified in the file. Run `python docs/live_probe.py --mobile` and `python docs/live_probe.py`. Each run creates a new deployed quiz; the desktop run also attempts to lock the secondary demo account for 15 minutes. Playwright is not an application runtime dependency.
