from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from src.auth import role_required
from src.errors import render_error
from src.services.question_service import (
    CHOICE_COUNT,
    CHOICE_LABELS,
    InvalidQuestion,
    MAX_POINTS,
    QuestionError,
    add_question,
    get_questions_page_data,
)

quiz_bp = Blueprint("quiz", __name__)


def _empty_form() -> dict[str, str | list[str]]:
    return {"content": "", "choices": [""] * CHOICE_COUNT, "correct_index": "", "points": "1"}


@quiz_bp.get("/quiz/<int:quiz_id>/questions")
@role_required("lecturer")
def questions_page(quiz_id: int):
    try:
        data = get_questions_page_data(
            current_app.config["DATABASE_PATH"], session["user_id"], quiz_id
        )
    except QuestionError as error:
        return render_error(error.status_code, error.message)
    return render_template(
        "questions.html",
        messages=[],
        form=_empty_form(),
        choice_labels=CHOICE_LABELS,
        max_points=MAX_POINTS,
        **data,
    )


@quiz_bp.post("/quiz/<int:quiz_id>/questions")
@role_required("lecturer")
def add_quiz_question(quiz_id: int):
    db_path = current_app.config["DATABASE_PATH"]
    choices = request.form.getlist("choices")
    form = {
        "content": request.form.get("content", ""),
        "choices": (choices + [""] * CHOICE_COUNT)[:CHOICE_COUNT],
        "correct_index": request.form.get("correct_index", ""),
        "points": request.form.get("points", ""),
    }

    try:
        add_question(
            db_path,
            session["user_id"],
            quiz_id,
            form["content"],
            choices,
            form["correct_index"],
            form["points"],
        )
    except QuestionError as error:
        return render_error(error.status_code, error.message)
    except InvalidQuestion as error:
        try:
            data = get_questions_page_data(db_path, session["user_id"], quiz_id)
        except QuestionError as page_error:
            return render_error(page_error.status_code, page_error.message)
        return (
            render_template(
                "questions.html",
                messages=error.messages,
                form=form,
                choice_labels=CHOICE_LABELS,
                max_points=MAX_POINTS,
                **data,
            ),
            422,
        )

    return redirect(url_for("quiz.questions_page", quiz_id=quiz_id))
