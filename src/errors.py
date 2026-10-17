"""Shared user-facing messages for HTTP errors."""

from flask import render_template


ERROR_MESSAGES = {
    400: "Email and password are required.",
    401: "Incorrect email or password.",
    403: "You do not have permission to access this page.",
    404: "The page you requested could not be found.",
    429: "Too many failed attempts. Try again in 15 minutes.",
}


def error_message(status_code: int) -> str:
    return ERROR_MESSAGES.get(status_code, "Something went wrong. Please try again.")


def render_error(status_code: int):
    return (
        render_template(
            "error.html",
            status_code=status_code,
            message=error_message(status_code),
        ),
        status_code,
    )
