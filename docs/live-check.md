# Live check P0 — 15/11/2026

URL bắt đầu duy nhất: **https://minilms-nhom7.onrender.com/**. URL giảng viên được cung cấp: https://minilms-nhom7.onrender.com/lecturer/dashboard.

Phương pháp lượt tự động: **automated browser-based functional testing** bằng Playwright và Chrome headless, context mới không chia sẻ cookie (tương đương phiên ẩn danh), desktop 1365×900 và giả lập cảm ứng 390×844. Tài khoản demo seed trong `SETUP.md` đăng nhập thành công. Không nhập URL trang con; script chỉ `goto` trang đầu rồi bấm liên kết, nút và xác nhận. Reload dùng để kiểm tra F5. Lượt điện thoại thật là **manual mobile testing** do Nguyễn Ngân An báo cáo, kèm 8 ảnh gốc, được ghi riêng bên dưới; được phân biệt với các mục reviewer độc lập bên dưới.

## Kết quả story

| Story | Điểm bắt đầu                                | Đường bấm                                                                       | Kết quả                                                               | Ảnh                                                                                                                     |
| ----- | ------------------------------------------------ | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| US01  | `/`, context mới                              | Điền tài khoản → Sign in                                                       | Đạt: giảng viên và sinh viên vào dashboard đúng vai trò       | [Giảng viên](images/live-check/mobile/US01-lecturer.png), [sinh viên](images/live-check/mobile/US01-student-mobile.png) |
| US02  | `/` → đăng nhập giảng viên               | + Create Quiz → điền tiêu đề → Create Quiz → xác nhận                     | Đạt: Draft được tạo; reload vẫn thấy quiz                       | [Tạo](images/live-check/mobile/US02-created.png), [F5](images/live-check/mobile/US02-after-F5.png)                        |
| US03  | `/` → giảng viên → tạo quiz               | Add Questions → điền câu hỏi, 4 lựa chọn, 1 đáp án đúng → Add Question | Đạt: lưu 1 câu hỏi                                                 | [Thêm câu](images/live-check/mobile/US03-added.png)                                                                     |
| US04  | `/` → giảng viên → tạo quiz → thêm câu | Publish Quiz → xác nhận                                                          | Đạt: Published; xuất hiện trên dashboard sinh viên                | [Published](images/live-check/mobile/US04-published.png)                                                                  |
| US06  | `/`, context sinh viên mới                   | Sign in → dòng quiz vừa tạo → Take quiz → chọn đáp án                     | Đạt: câu hỏi và timer nhìn thấy; chọn radio được ở 390×844 | [Làm bài](images/live-check/mobile/US06-mobile-answer.png)                                                              |
| US08  | `/` → sinh viên → Take quiz                 | Chọn đáp án → Review & submit → Submit quiz → xác nhận                     | Đạt: Quiz submitted, điểm 1/1 (100%), thời gian nộp               | [Đã nộp](images/live-check/mobile/US08-mobile-submitted.png)                                                           |

Đợt chạy mobile đầy đủ: quiz **18**, nhãn `LIVE CHECK 20261115-150924`. Các quiz `LIVE CHECK` là dữ liệu kiểm tra thật, không phải dữ liệu dựng ảnh. Các lần chạy thử trước có thể để lại quiz nháp riêng; không xóa dữ liệu hay lượt nộp của người khác. Log đích đến: [mobile/results.json](images/live-check/mobile/results.json). Ảnh desktop và log được lưu riêng trong `images/live-check/desktop/`.

**6/6 story đi được bằng bấm trên URL thật trong trình duyệt tự động.** Đã bổ sung kết quả điện thoại thật do An cung cấp và các mục kết quả reviewer độc lập bên dưới. Chưa xác nhận triển khai bản sửa H9 hoặc đối chiếu phiếu M3.

## Tạo dữ liệu rồi tải lại

Tạo quiz riêng → xác nhận tạo → chụp trạng thái Draft → reload → kiểm tra đúng tiêu đề vẫn còn. Ảnh US02 trước/sau F5 ở bảng trên. Đây là persistence qua tải lại trang, chưa kết luận dữ liệu sống qua redeploy/restart Render. Xem thêm `adr/0003-hosting-sqlite-reseed.md` về SQLite trên hosting.

## Ba luật chuẩn bị để phá

| Luật                       | Cách thao tác từ trang đầu                                                                                                                       | Kết quả và H9                                                                                                                                                                                                                                                                                                                |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Quiz 0 câu                 | Giảng viên → Create Quiz → xác nhận → chưa thêm câu → xem Publish Quiz                                                                     | Nút bị khóa và hiện `A quiz must contain at least 1 question.`. [Ảnh](images/live-check/mobile/rule-empty-quiz.png). Ngăn sai đúng nhưng thiếu chỉ dẫn sửa; bản sửa local thêm `Open Add Questions, save a question with one correct answer, then publish again.`. Chưa triển khai bản sửa lên Render. |
| Bắt đầu quiz vừa đóng | Sinh viên mở dashboard có quiz Published; giảng viên đóng quiz đó ở phiên riêng; sinh viên bấm Take/Retake trên dashboard chưa reload | Bị chặn: `This quiz is closed, so you can't start it. Contact your lecturer if you need access.` Nói rõ sự việc, lý do, bước tiếp. [Ảnh](images/live-check/mobile/rule-closed-quiz.png).                                                                                                                            |
| Sai mật khẩu lần 5       | Phiên mới → dùng tài khoản demo phụ `minh.student@example.edu` → sai mật khẩu 5 lần                                                      | Đạt: hiện `Too many failed attempts. Try again in 15 minutes.`. [Ảnh lần thứ 5](images/live-check/desktop/rule-fifth-wrong-password.png). Tài khoản này bị khóa tạm 15 phút; không dùng tài khoản đó cho phần demo chính.                                                                                 |

Không nhận đã thử live tình huống nộp hai lần. Chọn ba tình huống trên cho buổi demo; bảo vệ nộp hai lần có trong test US08 hiện hữu.

## Lỗi và bản sửa

| Lỗi                                                | Issue                                                      | Bản sửa                                                                                          | Test                                                                                                                                                   | Trạng thái                                                                                                                  |
| --------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| H9: lỗi quiz rỗng thiếu hướng dẫn khắc phục | [Issue #172 — bug](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/issues/172) | [PR #176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176): bổ sung bước Add Questions, lưu câu có đáp án đúng rồi publish lại trong `src/errors.py` | `test_us04_03_quiz_with_0_questions_cannot_be_published`: kiểm tra cả POST bị từ chối và GET trang quản lý; red trước sửa, green sau sửa | PR #176 đang mở, chưa merge/deploy; chỉ gồm hai file code/test. PR #171 giữ tài liệu và bằng chứng, không chứa thay đổi triển khai H9. [Chi tiết](review/live-check-h9-pr.md) |

Không tìm thấy ngõ cụt hoặc bước buộc nhập URL trong các luồng đã chạy. Không tính lỗi selector của script hay lỗi quyền thư mục tạm của môi trường là bug sản phẩm.

Kiểm tra local: bộ test nền **273 passed** (538,56 giây); lượt này bắt đầu trước khi sửa thông báo. Sau sửa, chạy riêng toàn bộ `tests/test_p0_us04_publish.py`: **8 passed** (27,86 giây). Test hồi quy quiz rỗng đã được chạy red trước sửa. `git diff --check`, kiểm tra cú pháp script và các liên kết bằng chứng đều đạt. Các số liệu này là kết quả lịch sử, không phải lượt chạy mới. CI của [PR #171](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/171) và [PR #176](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/pull/176) đã xanh tại thời điểm kiểm tra trước cập nhật tài liệu này; xem kết quả CI của commit mới trên GitHub.

## Hai thay đổi sau M3

Commit [47805a1](https://github.com/SE-FDA-NEU/Gr7_AI66A_SE/commit/47805a14d4835b9032807f16ace1adb0a8abd197), ngày **24/10/2026 13:36 +07**, liên quan #108, mô tả bốn thay đổi trong yêu cầu. Chọn **sửa câu hỏi** và **điều chỉnh số lượt làm bài**. Script đã sửa nội dung câu hỏi và lưu giới hạn từ 1 thành 2, reload kiểm tra vẫn là 2 trên Render.

| Thay đổi            | Trước                                                               | Sau trên URL thật                                                                |
| --------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Sửa câu hỏi        | [Wireframe US03 ngày 18/10](images/m3-fixes/edit-question-before.png) | [Nội dung đã sửa, nút chỉnh sửa](images/m3-fixes/edit-question-after.png)    |
| Cấu hình số lượt | [Wireframe US04 ngày 18/10](images/m3-fixes/attempt-limit-before.png) | [Maximum attempts = 2 sau lưu và reload](images/m3-fixes/attempt-limit-after.png) |

**Giới hạn bằng chứng:** ảnh trước là wireframe có sẵn trong repo, không phải ảnh chụp sản phẩm M3. Chúng minh họa thiết kế trước, không chứng minh riêng rằng tính năng từng không tồn tại. Chưa có phiếu phản hồi M3 thật của giảng viên: chưa thể xác nhận hai thay đổi này đáp ứng đúng từng nhận xét. Cần bổ sung phiếu và đối chiếu trước khi ký nghiệm thu M3. Nguồn ảnh và commit ghi trong [m3-fixes/README.md](images/m3-fixes/README.md).

## Kịch bản demo 5 phút

1. 0:00–0:30: mở `/` trong phiên ẩn danh, đăng nhập giảng viên.
2. 0:30–1:15: tạo quiz có nhãn DEMO, F5 chứng minh còn dữ liệu; chỉ ra thông báo chặn quiz 0 câu.
3. 1:15–2:15: thêm 1 câu, 4 lựa chọn, 1 đáp án đúng; xuất bản và xác nhận.
4. 2:15–3:45: mở `/` trong phiên điện thoại riêng, đăng nhập sinh viên, bấm Take quiz; chỉ timer, chọn đáp án, review, nộp và xem điểm.
5. 3:45–4:30: trình bày hai cặp ảnh, commit 24/10 và phiếu M3 khi có.
6. 4:30–5:00: phá một luật theo chỉ định. Với luật khóa đăng nhập, dùng tài khoản demo phụ; với quiz đóng, chuẩn bị sẵn dashboard sinh viên chưa reload và phiên giảng viên.

## Kiểm tra điện thoại thật — Nguyễn Ngân An

Ngày **15/11/2026**, thiết bị **iPhone 14 Pro**, trình duyệt **Safari** (theo người kiểm tra cung cấp). Giờ hiển thị trên các ảnh: **16:41–16:49**; kết quả nộp ghi rõ **16:49 UTC+7**. Người kiểm tra báo đã làm toàn bộ các bước tạo quiz, tải lại, thử publish khi chưa có câu hỏi, thêm câu, xuất bản, đăng nhập sinh viên, làm và nộp bài; không gặp lỗi ngoài các validation dự kiến.

Tên quiz thực tế trong ảnh là **`iphone 14 pro + safari`**, thay cho tên gợi ý `PHONE REVIEW`. Ảnh được sao chép nguyên bản từ các tệp người dùng gửi, không dựng lại hoặc chỉnh sửa.

| Hạng mục | Kết quả do người kiểm tra báo cáo | Bằng chứng và giới hạn |
| --- | --- | --- |
| US01 — đăng nhập, đổi vai trò | Đạt: đăng nhập giảng viên, đăng xuất rồi đăng nhập sinh viên | [Dashboard sinh viên](images/live-check/iphone-14-pro-safari/01-student-dashboard.jpg); các ảnh quản lý quiz chứng minh truy cập vai trò giảng viên, không có ảnh riêng màn hình đăng nhập |
| US02 — tạo quiz và tải lại | Đạt: tạo quiz 30 phút, tải lại vẫn còn | [Quiz vừa tạo, Draft, 0 câu](images/live-check/iphone-14-pro-safari/03-created-empty-quiz.jpg). Persistence sau tải lại là xác nhận của người kiểm tra; chưa có cặp ảnh riêng trước/sau reload |
| US03 — thêm câu hỏi | Đạt: thêm câu `1+1`, 4 lựa chọn, 1 đáp án đúng | [Validation chưa chọn đáp án đúng](images/live-check/iphone-14-pro-safari/05-required-correct-choice.jpg); câu hỏi xuất hiện trên màn hình làm bài |
| US04 — xuất bản | Đạt: xuất bản rồi quiz xuất hiện cho sinh viên | [Nút Publish được bật](images/live-check/iphone-14-pro-safari/06-publish-enabled.jpg), [dashboard sinh viên có quiz](images/live-check/iphone-14-pro-safari/01-student-dashboard.jpg); ảnh nút bật chưa phải ảnh xác nhận Published |
| US06 — bắt đầu và chọn đáp án | Đạt: timer nhìn thấy và chọn đáp án được | [Màn hình làm bài, timer 29:54](images/live-check/iphone-14-pro-safari/07-take-quiz-timer.jpg). Ảnh chụp trước khi chọn radio; thao tác chọn được xác nhận qua báo cáo và kết quả chấm điểm |
| US08 — nộp bài | Đạt: review, xác nhận nộp, nhận điểm | [Quiz submitted, 1/1 (100%), 16:49 UTC+7](images/live-check/iphone-14-pro-safari/08-submitted-result.jpg) |
| BR3 — không publish quiz 0 câu | Đạt về ngăn xuất bản: nút Publish bị khóa, thông báo ít nhất 1 câu | [Nút bị khóa và lý do](images/live-check/iphone-14-pro-safari/04-empty-quiz-publish-blocked.jpg). Thông báo Render trong ảnh vẫn thiếu câu hướng dẫn phục hồi của bản sửa H9 trong repo; chưa xác nhận H9 đã triển khai |
| Validation bổ sung | Chặn nội dung câu hỏi rỗng và chưa chọn đáp án đúng | [Trường câu hỏi bắt buộc](images/live-check/iphone-14-pro-safari/02-required-question.jpg), [chọn đáp án đúng bắt buộc](images/live-check/iphone-14-pro-safari/05-required-correct-choice.jpg); đây là thông báo validation gốc của trình duyệt |

Kết quả này ghi nhận kiểm tra **điện thoại thật bởi An**, không phải lượt tự chạy của trợ lý. Kết quả của An được ghi riêng với các mục do reviewer khác bổ sung trong bảng dưới.

## Reviewer độc lập với An — kết quả do reviewer bổ sung

Các lượt kiểm tra trong bảng này là **manual mobile testing** do reviewer bổ sung. Yêu cầu: reviewer dùng điện thoại của mình, không sao chép kết quả của An; chỉ nhập URL trang đầu một lần, làm lại ít nhất 2 story, rồi phá một luật bất kỳ. Giữ nguyên các kết quả và ảnh mà reviewer đã cung cấp.

| Người kiểm tra | Ngày/giờ +07 | Thiết bị/trình duyệt | Story 1 + kết quả/ảnh                                                         | Story 2 + kết quả/ảnh                                                           | Luật + kết quả/ảnh                                                                                                                              |
| ----------------- | -------------- | ------------------------ | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Le Ngoc Anh Thu   | 16:56          | Honor X6C - Chrome       | [US04](images/live-check/reviewer/thu-01-student-dashboard.png) | [US08](images/live-check/reviewer/thu-03-submitted.png)           | [BR3 - A quiz cannot be published unless it contains at least 1 question](images/live-check/reviewer/thu-04-empty-quiz-rule.png)   |
| Nguyen Thanh Lan  | 17:05          | Honor X7C - Chrome       | [US06](images/live-check/reviewer/lan-02-take-timer.png)        | [US01](images/live-check/reviewer/lan-06-too-many-login-item.png) | [BR5 - Each student may submit up to the quiz&#39;s configured attempt limit](images/live-check/reviewer/lan-05-double-submit.png) |

## Chạy lại tự động

Cài Playwright vào môi trường kiểm tra (`python -m pip install playwright`); script dùng Chrome tại đường dẫn Windows ghi trong file. Chạy `python docs/live_probe.py --mobile` và `python docs/live_probe.py`. Mỗi lần chạy tạo một quiz thật mới; lần desktop thử khóa tài khoản demo phụ 15 phút. Không đưa Playwright vào dependencies runtime của ứng dụng.
