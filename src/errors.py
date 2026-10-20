from flask import render_template


ERROR_MESSAGES = {
    400: "Email and password are required.",
    401: "Incorrect email or password.",
    403: "You do not have permission to access this page.",
    404: "The page you requested could not be found.",
    429: "Too many failed attempts. Try again in 15 minutes.",
}

QUIZ_NOT_FOUND = (
    "This quiz could not be found. It may have been removed. "
    "Go back to the dashboard to choose another quiz."
)
QUIZ_NOT_PUBLISHED = (
    "This quiz hasn't been published yet, so you can't start it. "
    "Check back later or contact your lecturer."
)
QUIZ_CLOSED = (
    "This quiz is closed, so you can't start it. "
    "Contact your lecturer if you need access."
)
ALREADY_SUBMITTED = (
    "You have already submitted this quiz, and each quiz allows only one submission. "
    "Go back to the dashboard to see other quizzes."
)
ATTEMPT_NOT_STARTED = (
    "You haven't started this quiz yet, so there is nothing to show. "
    "Go back to the dashboard and click Take quiz."
)
NOT_YOUR_ATTEMPT = (
    "This quiz attempt belongs to another student, so you can't view or change it. "
    "Go back to the dashboard and open your own quiz."
)
AUTO_SUBMITTED = (
    "Time ran out, so your attempt was submitted automatically with the answers "
    "saved before the deadline. Contact your lecturer if you think this is a mistake."
)
UNANSWERED_NOT_CONFIRMED = (
    "Some questions are still unanswered, so the quiz was not submitted. "
    "Answer them, or tick the confirmation box to submit anyway."
)
ATTEMPT_NOT_SUBMITTED = (
    "You haven't submitted this quiz yet, so there is no submission to show. "
    "Go back to the dashboard to continue the quiz."
)
ATTEMPT_NOT_FOUND = (
    "This attempt could not be found for the selected quiz. "
    "Return to the quiz attempts list and choose a listed attempt."
)
INVALID_CHOICE = (
    "The selected option does not belong to this question, so it was not saved. "
    "Go back to the question and choose one of the listed options."
)
QUESTION_NOT_FOUND = (
    "This question number does not exist in the quiz. "
    "Use the question numbers on the quiz page to move between questions."
)
NOT_QUIZ_OWNER = (
    "This quiz belongs to another lecturer, so you cannot edit it. "
    "Go back to your quiz list."
)
QUESTION_CONTENT_REQUIRED = "Please enter a question."
CHOICES_REQUIRED = "Please enter all four options."
SELECT_CORRECT_OPTION = "Please select one correct option."
INVALID_POINTS = "Points must be a positive whole number within the supported range."

# Quiz publication and ownership messages (US04, BR2, BR3)
NOT_QUIZ_OWNER = (
    "Bạn không có quyền sửa quiz này vì nó thuộc giảng viên khác. "
    "Hãy quay lại danh sách quiz của bạn. (You do not have permission to edit this quiz.)"
)
QUIZ_NO_QUESTIONS = (
    "Chưa thể publish: bài quiz phải có ít nhất 1 câu hỏi. "
    "(A quiz must contain at least 1 question.)"
)
QUIZ_ALREADY_PUBLISHED = (
    "Bài quiz này đã được publish trước đó. "
    "Không thể publish lại bài quiz đang hoạt động."
)
QUIZ_DRAFT_CANNOT_BE_CLOSED = (
    "Bài quiz đang ở trạng thái bản nháp (Draft), phải được publish trước khi đóng. "
    "(A quiz must be published before it can be closed.)"
)
QUIZ_ALREADY_CLOSED = (
    "Bài quiz này đã được đóng trước đó. "
    "(This quiz is already closed.)"
)


def quiz_question_missing_correct_choice(position: int) -> str:
    return (
        f"Chưa thể publish: câu {position} chưa có đáp án đúng. "
        "Hãy chọn đúng 1 đáp án cho mỗi câu. (Please select one correct option.)"
    )


def quiz_question_insufficient_choices(position: int) -> str:
    return (
        f"Chưa thể publish: câu {position} phải có ít nhất 2 đáp án lựa chọn."
    )


ERROR_TITLES = {
    400: "Yêu cầu không hợp lệ (Bad Request)",
    401: "Chưa đăng nhập (Unauthorized)",
    403: "Không có quyền truy cập (Access Denied)",
    404: "Không tìm thấy trang (Not Found)",
    409: "Xung đột trạng thái (Conflict)",
    422: "Không thể xử lý yêu cầu (Validation Error)",
    429: "Quá nhiều yêu cầu (Too Many Requests)",
}


def error_title(status_code: int) -> str:
    return ERROR_TITLES.get(status_code, "Thông báo lỗi (Error)")


def error_message(status_code: int) -> str:
    return ERROR_MESSAGES.get(status_code, "Something went wrong. Please try again.")


def render_error(status_code: int, message: str | None = None, title: str | None = None):
    return (
        render_template(
            "error.html",
            status_code=status_code,
            title=title or error_title(status_code),
            message=message or error_message(status_code),
        ),
        status_code,
    )
