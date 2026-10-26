# Mini LMS - Test Plan & Test Cases

| Phiên bản | Ngày giờ | Người cập nhật | Nội dung |
|---|---|---|---|
| 1.0 | 2026-10-25 | Dao Ngoc Hien | Tạo tài liệu; thêm mục US09 (issue #112) |

Tài liệu này ghi các test case được thiết kế theo slide Software Testing tuần 11 (equivalence partitioning, boundary value analysis, decision table, unhappy path) và làm theo TDD: viết test từ acceptance criteria (AC) và business rule (BR) trước, sau đó mới viết code. Cột **Expected** lấy từ AC/BR trong `requirements.md` và `ui.md`, không chép từ output của code.

Chạy test: `pytest tests/test_us09.py -v`

---

## US09 - Student sees an automatically calculated result

Issue: #112 · Test file: [`tests/test_us09.py`](../tests/test_us09.py)

### Căn cứ

| AC | Given | When | Then |
|---|---|---|---|
| AC1 | Bài đã nộp, đúng 8/10 câu | SV mở trang kết quả | Hiện `8/10` và `80%` |
| AC2 | Giảng viên bật answer review | SV mở kết quả | Cả 10 câu hiện đáp án đã chọn và đúng/sai |
| AC3 | Giảng viên tắt answer review | SV mở kết quả | Thấy điểm, không thấy đáp án đúng |
| AC4 | Bài chưa nộp | SV mở route kết quả | Không hiện điểm cuối cùng |

- `attempt.score` = số câu đúng / tổng số câu, tỉ lệ 0–1 (US08). Phần trăm hiển thị = `score × 100` **làm tròn half-up** (12.5 → 13), không cắt phần thập phân (xem `ui.md`, Thay đổi 3).
- BR1: khách → `/login`, giảng viên → 403. BR5: mỗi SV có tối đa 1 bài đã nộp/quiz. BR6: điểm đã nộp không đổi.
- US11/US13: hết giờ thì bài tự nộp, điểm tính từ đáp án đã lưu đến deadline.

### Chênh lệch với requirements.md

`requirements.md` (mục 6) liệt kê route `/student/quiz/:id/grade` cho kết quả. Nhóm quyết định **hiện điểm trên `/student/quiz/:id/submitted`** (trang đã có từ US08, đã có kiểm tra 404 khi chưa nộp và phân quyền BR1) và không tạo `/grade`. Định dạng hiển thị: `Score: 8/10 (80%)`.

### Test case

| ID | Precondition | Input | Expected | Technique | Test function |
|---|---|---|---|---|---|
| US09-01 | — | correct=10, total=10 | `10/10`, `100%` | EP đúng hết + BVA max | `test_result_summary[10-10-10/10-100]` |
| US09-02 | — | correct=8, total=10 | `8/10`, `80%` (AC1) | EP đúng một phần | `test_result_summary[8-10-8/10-80]` |
| US09-03 | — | correct=0, total=10 | `0/10`, `0%` | EP sai hết + BVA min | `test_result_summary[0-10-0/10-0]` |
| US09-04 | — | correct=2, total=3 | `2/3`, `67%` (không cắt thành 66) | BVA làm tròn | `test_result_summary[2-3-2/3-67]` |
| US09-05 | — | correct=1, total=3 | `1/3`, `33%` | BVA làm tròn | `test_result_summary[1-3-1/3-33]` |
| US09-06 | — | correct=1, total=8 (12.5%) | `1/8`, `13%` (half-up, không làm tròn về số chẵn) | BVA đúng mốc .5 | `test_result_summary[1-8-1/8-13]` |
| US09-07 | — | correct=0, total=0 | `0/0`, `0%`, không lỗi chia cho 0 | Biên lỗi | `test_result_summary[0-0-0/0-0]` |
| US09-08 | Duc làm quiz 3 câu, không trả lời câu nào, nộp với confirm=yes | GET `/submitted` | `Score: 0/3 (0%)` | EP không trả lời | `test_unanswered_attempt_scores_zero` |
| US09-09 | Duc trả lời đúng 1/1 rồi nộp | GET `/submitted` hai lần | 200, `Score: 1/1 (100%)`; lần 2 giống lần 1 (BR6) | Tích hợp AC1 | `test_submitted_page_shows_score` |
| US09-10 | Duc đúng 2/3, đồng hồ qua mốc 20 phút | GET `/take?q=1`, mở trang được chuyển tới | 302 → `submitted?timeout=1`; thông báo tự nộp; `Score: 2/3 (67%)` | EP nộp tự động | `test_auto_submitted_attempt_shows_score` |
| US09-11 | Duc đã bắt đầu, chưa nộp | GET `/submitted` | 404, không có `Score:` (AC4) | Decision table R2 | `test_unsubmitted_attempt_shows_no_score` |
| US09-12 | Duc đã nộp quiz 1, Lan chưa làm | Lan GET `/student/quiz/1/submitted` | 404, không thấy điểm của Duc | Decision table R3 | `test_other_students_result_is_not_visible` |
| US09-13 | Đăng nhập giảng viên Ngan | GET `/submitted` | 403 (BR1) | Decision table R4 | `test_lecturer_cannot_open_result` |
| US09-14 | Chưa đăng nhập | GET `/submitted` | 302 → `/login` (BR1) | Decision table R5 | `test_guest_result_redirects_to_login` |
| US09-15 | Giảng viên bật answer review (AC2) | — | **Blocked** — chờ issue riêng: cần cột `quiz.show_answers` và UI giảng viên | — | — |
| US09-16 | Giảng viên tắt answer review (AC3) | — | **Blocked** — chờ issue riêng: cần cột `quiz.show_answers` và UI giảng viên | — | — |

US09-01..07 kiểm tra hàm thuần `attempt_service.result_summary(correct, total)` bằng `pytest.mark.parametrize`, không qua Flask hay DB. US09-08..14 chạy qua Flask test client.

### Decision table - `GET /student/quiz/:id/submitted`

| Rule | Đã đăng nhập | Là student | Có bài **của mình** đã nộp | Kết quả | Test case |
|---|---|---|---|---|---|
| R1 | Y | Y | Y | 200 + `Score: n/N (p%)` | US09-08, 09, 10 |
| R2 | Y | Y | N (chưa nộp) | 404, không có điểm | US09-11 |
| R3 | Y | Y | N (chỉ người khác nộp) | 404, không có điểm | US09-12 |
| R4 | Y | N (giảng viên) | – | 403 | US09-13 |
| R5 | N | – | – | 302 → `/login` | US09-14 |

Route lấy bài theo `session["user_id"]`, nên SV không thể chỉ định bài của người khác; trường hợp "bài người khác" rơi vào R3.
