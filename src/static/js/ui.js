document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".toast").forEach(function (toast) {
        var dismiss = function () {
            toast.classList.add("toast-hidden");
            window.setTimeout(function () {
                toast.remove();
            }, 220);
        };

        toast.querySelector(".toast-dismiss").addEventListener("click", dismiss);
        window.setTimeout(dismiss, 5000);
    });

    document.addEventListener("submit", function (event) {
        var form = event.target;
        var message = form.dataset.confirm;
        if (!message) {
            return;
        }

        if (typeof HTMLDialogElement === "undefined") {
            if (!window.confirm(message)) {
                event.preventDefault();
            }
            return;
        }

        if (form.dataset.confirmed === "true") {
            delete form.dataset.confirmed;
            return;
        }

        event.preventDefault();
        var submitter = event.submitter;
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
        var closeDialog = function () {
            dialog.close();
            dialog.remove();
        };

        cancel.addEventListener("click", closeDialog);
        dialog.addEventListener("cancel", function (cancelEvent) {
            cancelEvent.preventDefault();
            closeDialog();
        });
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
