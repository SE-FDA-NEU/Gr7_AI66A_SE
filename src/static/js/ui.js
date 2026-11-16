// Hành vi dùng chung: tự ẩn thông báo flash và hỏi xác nhận trước các form có data-confirm.
document.addEventListener("DOMContentLoaded", function () {
    // Chỉ chạy sau khi HTML đã dựng xong để tìm thấy các toast trong trang.
    document.querySelectorAll(".toast").forEach(function (toast) {
        // Ẩn toast bằng class để CSS chạy hiệu ứng, rồi xóa khỏi DOM.
        var dismiss = function () {
            toast.classList.add("toast-hidden");
            window.setTimeout(function () {
                toast.remove();
            }, 220);
        };

        // Cho phép đóng thủ công hoặc tự đóng sau 5 giây.
        toast.querySelector(".toast-dismiss").addEventListener("click", dismiss);
        window.setTimeout(dismiss, 5000);
    });

    document.addEventListener("submit", function (event) {
        // Lắng nghe submit ở document để áp dụng cho cả form được tạo động.
        var form = event.target;
        var message = form.dataset.confirm;
        if (!message) {
            return;
        }

        // Trình duyệt cũ không có dialog: dùng hộp confirm mặc định làm phương án thay thế.
        if (typeof HTMLDialogElement === "undefined") {
            if (!window.confirm(message)) {
                event.preventDefault();
            }
            return;
        }

        // Lần submit thứ hai đã được người dùng xác nhận nên cho form gửi tiếp.
        if (form.dataset.confirmed === "true") {
            delete form.dataset.confirmed;
            return;
        }

        // Chặn submit đầu tiên để dựng hộp thoại xác nhận.
        event.preventDefault();
        var submitter = event.submitter;
        // Tạo dialog bằng DOM API và gán textContent để tránh diễn giải nội dung thành HTML.
        var dialog = document.createElement("dialog");
        dialog.className = "confirm-dialog";

        var content = document.createElement("div");
        content.className = "confirm-dialog-content";

        var title = document.createElement("h2");
        title.textContent = form.dataset.confirmTitle || "Please confirm";

        var description = document.createElement("p");
        description.textContent = message;

        var actions = document.createElement("div");
        actions.className = "confirm-dialog-actions";

        var cancel = document.createElement("button");
        cancel.type = "button";
        cancel.className = "btn btn-secondary";
        cancel.textContent = "Cancel";

        var confirm = document.createElement("button");
        confirm.type = "button";
        confirm.className = "btn btn-primary";
        confirm.textContent = form.dataset.confirmLabel || "Continue";

        actions.append(cancel, confirm);
        content.append(title, description, actions);
        dialog.append(content);
        // Đóng và xóa dialog khỏi DOM để không tích lũy phần tử sau nhiều lần dùng.
        var closeDialog = function () {
            dialog.close();
            dialog.remove();
        };

        cancel.addEventListener("click", closeDialog);
        dialog.addEventListener("cancel", function (cancelEvent) {
            cancelEvent.preventDefault();
            closeDialog();
        });
        // Đánh dấu đã xác nhận rồi gửi lại form, giữ đúng nút submit ban đầu nếu có.
        confirm.addEventListener("click", function () {
            closeDialog();
            form.dataset.confirmed = "true";
            if (typeof form.requestSubmit === "function") {
                if (submitter) {
                    form.requestSubmit(submitter);
                } else {
                    form.requestSubmit();
                }
            } else {
                form.submit();
            }
        });

        document.body.append(dialog);
        dialog.showModal();
        cancel.focus();
    });
});
