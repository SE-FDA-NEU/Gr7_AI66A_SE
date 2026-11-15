# Live check P0 — 15/11/2026

URL bắt đầu duy nhất: **https://minilms-nhom7.onrender.com/**. URL giảng viên được cung cấp: https://minilms-nhom7.onrender.com/lecturer/dashboard.

Kiểm tra bằng Chrome headless, context mới không chia sẻ cookie (tương đương phiên ẩn danh), desktop 1365×900 và giả lập cảm ứng 390×844. Đây **chưa phải kiểm tra trên điện thoại vật lý**. Tài khoản demo seed trong `SETUP.md` đăng nhập thành công. Không nhập URL trang con; script chỉ `goto` trang đầu rồi bấm liên kết, nút và xác nhận. Reload dùng để kiểm tra F5.

## Kết quả story

| Story | Điểm bắt đầu | Đường bấm | Kết quả | Ảnh |
| --- | --- | --- | --- | --- |
| US01 | `/`, context mới | Điền tài khoản → Sign in | Đạt: giảng viên và sinh viên vào dashboard đúng vai trò | [Giảng viên](images/live-check/mobile/US01-lecturer.png), [sinh viên](images/live-check/mobile/US01-student-mobile.png) |
| US02 | `/` → đăng nhập giảng viên | + Create Quiz → điền tiêu đề → Create Quiz → xác nhận | Đạt: Draft được tạo; reload vẫn thấy quiz | [Tạo](images/live-check/mobile/US02-created.png), [F5](images/live-check/mobile/US02-after-F5.png) |
| US03 | `/` → giảng viên → tạo quiz | Add Questions → điền câu hỏi, 4 lựa chọn, 1 đáp án đúng → Add Question | Đạt: lưu 1 câu hỏi | [Thêm câu](images/live-check/mobile/US03-added.png) |
| US04 | `/` → giảng viên → tạo quiz → thêm câu | Publish Quiz → xác nhận | Đạt: Published; xuất hiện trên dashboard sinh viên | [Published](images/live-check/mobile/US04-published.png) |
| US06 | `/`, context sinh viên mới | Sign in → dòng quiz vừa tạo → Take quiz → chọn đáp án | Đạt: câu hỏi và timer nhìn thấy; chọn radio được ở 390×844 | [Làm bài](images/live-check/mobile/US06-mobile-answer.png) |
| US08 | `/` → sinh viên → Take quiz | Chọn đáp án → Review & submit → Submit quiz → xác nhận | Đạt: Quiz submitted, điểm 1/1 (100%), thời gian nộp | [Đã nộp](images/live-check/mobile/US08-mobile-submitted.png) |

Đợt chạy mobile đầy đủ: quiz **18**, nhãn `LIVE CHECK 20261115-150924`. Các quiz `LIVE CHECK` là dữ liệu kiểm tra thật, không phải dữ liệu dựng ảnh. Các lần chạy thử trước có thể để lại quiz nháp riêng; không xóa dữ liệu hay lượt nộp của người khác. Log đích đến: [mobile/results.json](images/live-check/mobile/results.json). Ảnh desktop và log được lưu riêng trong `images/live-check/desktop/`.

**6/6 story đi được bằng bấm trên URL thật trong trình duyệt tự động.** Chưa ký nghiệm thu thiết bị vật lý, reviewer độc lập, triển khai bản sửa H9 hoặc đối chiếu phiếu M3.

## Tạo dữ liệu rồi tải lại

Tạo quiz riêng → xác nhận tạo → chụp trạng thái Draft → reload → kiểm tra đúng tiêu đề vẫn còn. Ảnh US02 trước/sau F5 ở bảng trên. Đây là persistence qua tải lại trang, chưa kết luận dữ liệu sống qua redeploy/restart Render. Xem thêm `adr/0003-hosting-sqlite-reseed.md` về SQLite trên hosting.

## Ba luật chuẩn bị để phá

| Luật | Cách thao tác từ trang đầu | Kết quả và H9 |
| --- | --- | --- |
| Quiz 0 câu | Giảng viên → Create Quiz → xác nhận → chưa thêm câu → xem Publish Quiz | Nút bị khóa và hiện `A quiz must contain at least 1 question.`. [Ảnh](images/live-check/mobile/rule-empty-quiz.png). Ngăn sai đúng nhưng thiếu chỉ dẫn sửa; bản sửa local thêm `Open Add Questions, save a question with one correct answer, then publish again.`. Chưa triển khai bản sửa lên Render. |
| Bắt đầu quiz vừa đóng | Sinh viên mở dashboard có quiz Published; giảng viên đóng quiz đó ở phiên riêng; sinh viên bấm Take/Retake trên dashboard chưa reload | Bị chặn: `This quiz is closed, so you can't start it. Contact your lecturer if you need access.` Nói rõ sự việc, lý do, bước tiếp. [Ảnh](images/live-check/mobile/rule-closed-quiz.png). |
| Sai mật khẩu lần 5 | Phiên mới → dùng tài khoản demo phụ `minh.student@example.edu` → sai mật khẩu 5 lần | Đạt: hiện `Too many failed attempts. Try again in 15 minutes.`. [Ảnh lần thứ 5](images/live-check/desktop/rule-fifth-wrong-password.png). Tài khoản này bị khóa tạm 15 phút; không dùng tài khoản đó cho phần demo chính. |

Không nhận đã thử live tình huống nộp hai lần. Chọn ba tình huống trên cho buổi demo; bảo vệ nộp hai lần có trong test US08 hiện hữu.

## Lỗi và bản sửa

| Lỗi | Issue | Bản sửa | Test | Trạng thái |
| --- | --- | --- | --- | --- |
| H9: lỗi quiz rỗng thiếu hướng dẫn khắc phục | [Nội dung issue, nhãn bug](review/live-check-h9-issue.md) | `src/errors.py`: bổ sung bước Add Questions, lưu câu có đáp án đúng rồi publish lại | `test_us04_03_quiz_with_0_questions_cannot_be_published`: kiểm tra cả POST bị từ chối và GET trang quản lý; red trước sửa, green sau sửa | Đã sửa local; chưa có issue/PR online vì không có xác thực GitHub. [Nội dung PR riêng](review/live-check-h9-pr.md) |

Không tìm thấy ngõ cụt hoặc bước buộc nhập URL trong các luồng đã chạy. Không tính lỗi selector của script hay lỗi quyền thư mục tạm của môi trường là bug sản phẩm.

Kiểm tra local: bộ test nền **273 passed** (538,56 giây); lượt này bắt đầu trước khi sửa thông báo. Sau sửa, chạy riêng toàn bộ `tests/test_p0_us04_publish.py`: **8 passed** (27,86 giây). Test hồi quy quiz rỗng đã được chạy red trước sửa. `git diff --check`, kiểm tra cú pháp script và các liên kết bằng chứng đều đạt. Chưa chạy CI trên nhánh PR vì chưa có PR online.

## Hai thay đổi sau M3

Commit [47805a1](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/commit/47805a14d4835b9032807f16ace1adb0a8abd197), ngày **24/10/2026 13:36 +07**, liên quan #108, mô tả bốn thay đổi trong yêu cầu. Chọn **sửa câu hỏi** và **điều chỉnh số lượt làm bài**. Script đã sửa nội dung câu hỏi và lưu giới hạn từ 1 thành 2, reload kiểm tra vẫn là 2 trên Render.

| Thay đổi | Trước | Sau trên URL thật |
| --- | --- | --- |
| Sửa câu hỏi | [Wireframe US03 ngày 18/10](images/m3-fixes/edit-question-before.png) | [Nội dung đã sửa, nút chỉnh sửa](images/m3-fixes/edit-question-after.png) |
| Cấu hình số lượt | [Wireframe US04 ngày 18/10](images/m3-fixes/attempt-limit-before.png) | [Maximum attempts = 2 sau lưu và reload](images/m3-fixes/attempt-limit-after.png) |

**Giới hạn bằng chứng:** ảnh trước là wireframe có sẵn trong repo, không phải ảnh chụp sản phẩm M3. Chúng minh họa thiết kế trước, không chứng minh riêng rằng tính năng từng không tồn tại. Chưa có phiếu phản hồi M3 thật của giảng viên: chưa thể xác nhận hai thay đổi này đáp ứng đúng từng nhận xét. Cần bổ sung phiếu và đối chiếu trước khi ký nghiệm thu M3. Nguồn ảnh và commit ghi trong [m3-fixes/README.md](images/m3-fixes/README.md).

## Kịch bản demo 5 phút

1. 0:00–0:30: mở `/` trong phiên ẩn danh, đăng nhập giảng viên.
2. 0:30–1:15: tạo quiz có nhãn DEMO, F5 chứng minh còn dữ liệu; chỉ ra thông báo chặn quiz 0 câu.
3. 1:15–2:15: thêm 1 câu, 4 lựa chọn, 1 đáp án đúng; xuất bản và xác nhận.
4. 2:15–3:45: mở `/` trong phiên điện thoại riêng, đăng nhập sinh viên, bấm Take quiz; chỉ timer, chọn đáp án, review, nộp và xem điểm.
5. 3:45–4:30: trình bày hai cặp ảnh, commit 24/10 và phiếu M3 khi có.
6. 4:30–5:00: phá một luật theo chỉ định. Với luật khóa đăng nhập, dùng tài khoản demo phụ; với quiz đóng, chuẩn bị sẵn dashboard sinh viên chưa reload và phiên giảng viên.

## Reviewer độc lập — chưa thực hiện

Reviewer dùng điện thoại của mình, không sao chép kết quả của An. Chỉ nhập URL trang đầu một lần; làm lại ít nhất US01 + US06 (nên thêm US08), rồi phá một luật bất kỳ.

| Người kiểm tra | Ngày/giờ +07 | Thiết bị/trình duyệt | Story 1 + kết quả/ảnh | Story 2 + kết quả/ảnh | Luật + kết quả/ảnh |
| --- | --- | --- | --- | --- | --- |
| Chưa điền | — | — | — | — | — |

## Chạy lại tự động

Cài Playwright vào môi trường kiểm tra (`python -m pip install playwright`); script dùng Chrome tại đường dẫn Windows ghi trong file. Chạy `python docs/live_probe.py --mobile` và `python docs/live_probe.py`. Mỗi lần chạy tạo một quiz thật mới; lần desktop thử khóa tài khoản demo phụ 15 phút. Không đưa Playwright vào dependencies runtime của ứng dụng.
