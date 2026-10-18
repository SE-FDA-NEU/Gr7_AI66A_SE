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
TIME_IS_UP = (
    "Time is up for this quiz, so your answer was not saved. "
    "Contact your lecturer if you think this is a mistake."
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


def error_message(status_code: int) -> str:
    return ERROR_MESSAGES.get(status_code, "Something went wrong. Please try again.")


def render_error(status_code: int, message: str | None = None):
    return (
        render_template(
            "error.html",
            status_code=status_code,
            message=message or error_message(status_code),
        ),
        status_code,
    )
