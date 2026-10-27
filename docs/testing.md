
# Mini LMS - Test Plan & Test Cases

| Phiên bản | Ngày giờ | Người cập nhật | Nội dung |
|---|---|---|---|
| 1.0 | 2026-10-25 | Dao Ngoc Hien | Tạo tài liệu; thêm US09 (issue #112) |
| 1.1 | 2026-10-28 | Nguyen Ngan An | Bổ sung US10 (#113) và US11 (#114) |

Tài liệu này ghi các test case được thiết kế theo slide Software Testing tuần 11 (equivalence partitioning, boundary value analysis, decision table, unhappy path).

Test case được xây dựng dựa trên acceptance criteria (AC) và business rule (BR). Cột **Expected** mô tả hành vi mong đợi, không sao chép từ kết quả chạy code.

---

## 1. What we test, and why

| Layer | Testing approach | Reason |
|---|---|---|
| Services | Unit tests với pytest | Kiểm tra business rules, tính điểm, thống kê và giới hạn thời gian |
| Repository | Integration tests với SQLite tạm | Kiểm tra dữ liệu được lưu và cập nhật chính xác |
| Routes | Flask test client | Kiểm tra HTTP response, phân quyền và điều hướng |
| Interface | Manual testing và kiểm tra HTML response | Xác nhận số liệu và đồng hồ hiển thị đúng |

### Risk Analysis

Các chức năng tính điểm, thống kê và giới hạn thời gian có mức độ rủi ro cao vì ảnh hưởng trực tiếp đến kết quả học tập.

US10 cần kiểm tra độ chính xác của điểm trung bình, tỷ lệ trả lời đúng và phân quyền giảng viên.

US11 cần kiểm tra đặc biệt tại mốc hết giờ vì sai lệch một giây có thể khiến bài làm bị nộp sớm hoặc cho phép làm quá thời gian.

---

## 2. Test Cases for P0 Stories

## US09 - Student sees an automatically calculated result

Issue: #112

Test file: `tests/test_us09.py`

### Acceptance Criteria

| AC | Given | When | Then |
|---|---|---|---|
| AC1 | Bài đã nộp, đúng 8/10 câu | SV mở trang kết quả | Hiện `8/10` và `80%` |
| AC2 | Giảng viên bật answer review | SV mở kết quả | Cả 10 câu hiện đáp án đã chọn và đúng/sai |
| AC3 | Giảng viên tắt answer review | SV mở kết quả | Thấy điểm, không thấy đáp án đúng |
| AC4 | Bài chưa nộp | SV mở route kết quả | Không hiện điểm cuối cùng |

### Business Rules

- `attempt.score` = số câu đúng / tổng số câu, tỷ lệ 0–1.
- Phần trăm hiển thị = `score × 100`, làm tròn half-up.
- BR1: Khách chuyển tới `/login`, giảng viên nhận 403.
- BR5: Mỗi sinh viên có tối đa một bài đã nộp cho mỗi quiz.
- BR6: Điểm bài đã nộp không thay đổi.
- US11/US13: Hết giờ, bài tự động nộp với các đáp án đã lưu.

### Chênh lệch với requirements.md

`requirements.md` liệt kê route `/student/quiz/:id/grade`.

Nhóm quyết định hiển thị kết quả trên `/student/quiz/:id/submitted`.

Định dạng: `Score: 8/10 (80%)`.

### Test Cases

| ID | Precondition | Input | Expected | Technique | Test function |
|---|---|---|---|---|---|
| US09-01 | — | correct=10, total=10 | `10/10`, `100%` | EP + BVA max | `test_result_summary[10-10-10/10-100]` |
| US09-02 | — | correct=8, total=10 | `8/10`, `80%` | EP | `test_result_summary[8-10-8/10-80]` |
| US09-03 | — | correct=0, total=10 | `0/10`, `0%` | EP + BVA min | `test_result_summary[0-10-0/10-0]` |
| US09-04 | — | correct=2, total=3 | `2/3`, `67%` | BVA rounding | `test_result_summary[2-3-2/3-67]` |
| US09-05 | — | correct=1, total=3 | `1/3`, `33%` | BVA rounding | `test_result_summary[1-3-1/3-33]` |
| US09-06 | — | correct=1, total=8 | `1/8`, `13%` | BVA half-up | `test_result_summary[1-8-1/8-13]` |
| US09-07 | — | correct=0, total=0 | `0/0`, `0%` | Error boundary | `test_result_summary[0-0-0/0-0]` |
| US09-08 | Không trả lời câu nào | GET `/submitted` | `Score: 0/3 (0%)` | EP | `test_unanswered_attempt_scores_zero` |
| US09-09 | Đúng 1/1, đã nộp | GET `/submitted` hai lần | Điểm giữ nguyên | Integration | `test_submitted_page_shows_score` |
| US09-10 | Đúng 2/3, hết 20 phút | GET `/take?q=1` | Auto-submit, `67%` | Timeout | `test_auto_submitted_attempt_shows_score` |
| US09-11 | Đã bắt đầu nhưng chưa nộp | GET `/submitted` | 404, không hiện điểm | Decision table | `test_unsubmitted_attempt_shows_no_score` |
| US09-12 | Sinh viên khác chưa làm | GET `/submitted` | 404, không lộ điểm | Authorization | `test_other_students_result_is_not_visible` |
| US09-13 | Giảng viên đăng nhập | GET `/submitted` | 403 | Error | `test_lecturer_cannot_open_result` |
| US09-14 | Chưa đăng nhập | GET `/submitted` | 302 tới `/login` | Error | `test_guest_result_redirects_to_login` |
| US09-15 | Answer review bật | Mở kết quả | Blocked: chờ chức năng review | — | — |
| US09-16 | Answer review tắt | Mở kết quả | Blocked: chờ chức năng review | — | — |

### Decision Table - Result Access

| Rule | Logged in | Student | Own submitted attempt | Expected |
|---|---|---|---|---|
| R1 | Yes | Yes | Yes | 200 + score |
| R2 | Yes | Yes | No | 404 |
| R3 | Yes | Yes | Only another student's | 404 |
| R4 | Yes | No | — | 403 |
| R5 | No | — | — | Redirect to login |

---

## US10 - Lecturer views quiz statistics

Issue: #113

Test file: `tests/test_quiz_features.py`

### Acceptance Criteria

| AC | Given | When | Then |
|---|---|---|---|
| AC1 | Quiz có các bài đã nộp | Giảng viên mở thống kê | Hiển thị tổng số lượt nộp |
| AC2 | Các bài đã nộp có điểm | Giảng viên mở thống kê | Hiển thị điểm trung bình chính xác |
| AC3 | Câu hỏi có dữ liệu trả lời | Giảng viên mở thống kê | Hiển thị tỷ lệ trả lời đúng từng câu |
| AC4 | Quiz chưa có bài nộp | Giảng viên mở thống kê | Hiển thị 0 và không gây lỗi |
| AC5 | Giảng viên không sở hữu quiz | Truy cập trang thống kê | Từ chối truy cập |

### Test Cases

| ID | Story | Input | Expected | Kind |
|---|---|---|---|---|
| US10-01 | Lecturer views quiz statistics | 20 submitted attempts | Total submitted = 20 | Normal |
| US10-02 | Lecturer views quiz statistics | Scores: 60%, 80%, 100% | Average score = 80% | Normal |
| US10-03 | Lecturer views quiz statistics | 15 correct out of 20 answers | Correct rate = 75% | Normal |
| US10-04 | Lecturer views another lecturer's quiz | Unauthorized lecturer | HTTP 403 | Error |
| US10-05 | Lecturer views quiz with no submissions | 0 submitted attempts | Total = 0, no division-by-zero error | Boundary |

### Test Design

- Equivalence Partitioning: Quiz có bài nộp và chưa có bài nộp.
- Boundary Value Analysis: 0 submissions.
- Unhappy Path: Giảng viên truy cập quiz không thuộc quyền sở hữu.
- Integration Testing: Kiểm tra dữ liệu thống kê qua service, route và giao diện.

### Business Rules

- Chỉ tính các attempts đã submitted.
- Điểm trung bình được tính từ các attempts hợp lệ.
- Tỷ lệ đúng từng câu dựa trên số câu trả lời đúng so với tổng số câu trả lời hợp lệ tương ứng.
- Không chia cho 0 khi quiz chưa có submissions.
- Giảng viên chỉ được xem thống kê quiz thuộc quyền sở hữu.

### Decision Table - Quiz Statistics

| Rule | Lecturer | Owns quiz | Submitted attempts | Expected |
|---|---|---|---|---|
| R1 | Yes | Yes | > 0 | Display statistics |
| R2 | Yes | Yes | 0 | Display zero statistics |
| R3 | Yes | No | Any | HTTP 403 |

---

## US11 - Quiz time limit

Issue: #114

Test file: `tests/test_time_limit.py`

### Acceptance Criteria

| AC | Given | When | Then |
|---|---|---|---|
| AC1 | Quiz có giới hạn 30 phút | Sinh viên bắt đầu | Đồng hồ bắt đầu tại 30:00 |
| AC2 | Sinh viên đang làm quiz | Thời gian đạt 30 phút | Bài được tự động nộp |
| AC3 | Giảng viên nhập thời lượng không hợp lệ | Tạo quiz | Hệ thống từ chối |
| AC4 | Sinh viên refresh trang | Quiz chưa hết giờ | Thời gian không bị reset |
| AC5 | Quiz chưa tới deadline | Sinh viên tiếp tục làm | Attempt vẫn active |
| AC6 | Quiz đã quá deadline | Sinh viên truy cập lại | Không được tiếp tục làm |

### Test Cases

| ID | Story | Input | Expected | Kind |
|---|---|---|---|---|
| US11-01 | Countdown starts correctly | Start a 30-minute quiz | Countdown = 1800 seconds | Normal |
| US11-02 | Automatic submission at deadline | Elapsed = 30:00 | Attempt submitted exactly once | Boundary, at limit |
| US11-03 | Reject invalid quiz duration | Duration = 0 | Reject, no quiz created | Error, zero |
| US11-04 | Reject invalid quiz duration | Duration = -1 | Reject, no quiz created | Error, below minimum |
| US11-05 | Reject invalid quiz duration | Duration = -5 | Reject, no quiz created | Error, negative |
| US11-06 | Refresh preserves remaining time | Elapsed = 18:00 | Remaining approximately 12:00, same attempt | Normal |
| US11-07 | Attempt active before deadline | Elapsed = 29:59 | Not submitted, approximately 1 second remains | Boundary, below limit |
| US11-08 | Attempt expired after deadline | Elapsed = 30:01 | Submitted, cannot continue answering | Boundary, above limit |


### Test Design

**Equivalence Partitioning**

- Valid duration: 30 minutes.
- Invalid duration: zero or negative.
- Active attempt: current time is before deadline.
- Expired attempt: current time is at or after deadline.

**Boundary Value Analysis**

- 29:59: Just below the 30-minute limit.
- 30:00: Exactly at the limit.
- 30:01: Just above the limit.

**Unhappy Path**

- Duration = 0.
- Duration = -1.
- Duration = -5.
- Accessing the quiz after expiration.

### Business Rules

- Quiz duration must be positive unless unlimited duration is explicitly supported.
- The countdown is based on the original attempt start time.
- Refreshing the page must not restart the countdown.
- An expired attempt must be submitted.
- An attempt must not be submitted more than once.
- Students cannot continue answering after the deadline.

### Decision Table - Quiz Time Limit

| Rule | Valid duration | Attempt started | Deadline reached | Expected |
|---|---|---|---|---|
| R1 | Yes | No | No | Allow starting quiz |
| R2 | Yes | Yes | No | Continue quiz |
| R3 | Yes | Yes | Yes | Auto-submit |
| R4 | No | No | — | Reject invalid duration |
| R5 | Yes | Yes | Already expired | No further answering |

### Test Results

| Story | Result | Status |
|---|---|---|
| US09 | See actual pytest output | Verify |
| US10 | 5 tests passed in prior verification | Passed previously |
| US11 | 8 tests passed | Passed |

The full pytest suite must be rerun after merging changes into main.

### Test Evidence

- US10: 5 automated tests passed.
- US11: 8 automated tests passed.
- Full test suite: `python -m pytest -v`.
- Test screenshots are included in the Milestone 4 submission.

---

## 3. What the Tests Found

### Mutation Testing – US11

To verify that automated tests can detect incorrect business rules, the quiz expiration condition is intentionally modified.

- Original rule: A quiz is automatically submitted when the time limit is reached.
- Mutation: Change the expiration condition to allow the quiz to continue at the exact deadline.
- Expected result: The boundary test at 30:00 fails.
- Recovery: Restore the original condition and rerun the tests.

**Mutation test result:** Pending verification.
