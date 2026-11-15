# Nguồn bằng chứng M3

Hai cặp ảnh là đối chiếu wireframe cũ với sản phẩm đang chạy, không phải xác nhận phiếu M3 của giảng viên.

| File | Nguồn |
| --- | --- |
| `edit-question-before.png` | Sao nguyên bản `docs/images/ui/US03/4_Data.png`, commit 797b912, 18/10/2026 18:08 +07; wireframe thêm câu, chưa có điều khiển sửa trong hình |
| `attempt-limit-before.png` | Sao nguyên bản `docs/images/ui/US04-wireframe.png`, commit 04a54b3, 18/10/2026 00:59 +07; wireframe quản lý, không có trường số lượt trong hình |
| `edit-question-after.png` | Ảnh thật Render, quiz 18, 15/11/2026; sửa câu thành `Live check edited: 2 + 2 = ?` |
| `attempt-limit-after.png` | Ảnh thật Render, quiz 18, 15/11/2026; lưu maximum attempts = 2 rồi reload |

Commit triển khai tính năng: `47805a14d4835b9032807f16ace1adb0a8abd197`, 24/10/2026 13:36 +07, refs #108.

Chờ phiếu M3 thật để điền: nguyên văn nhận xét, mục trong phiếu, người xác nhận, ngày xác nhận. Nếu giảng viên yêu cầu ảnh chụp sản phẩm trước M3, cần thay wireframe bằng ảnh M3 có nguồn xác định; không ghi wireframe là ảnh sản phẩm.
