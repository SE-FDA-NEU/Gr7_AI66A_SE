
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

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
    update_question,
)

from src.services.quiz_service import (
    InvalidQuiz,
    QuizServiceError,
    create_new_quiz,
    get_quiz_publish_details,
)


quiz_bp = Blueprint("quiz", __name__)


# ==========================================
# US02 - CREATE QUIZ
# ==========================================

@quiz_bp.get("/quiz/create")
@role_required("lecturer")
def create_quiz_page():
    """Display the Create Quiz form."""

    return render_template(
        "create_quiz.html",
        error=None,
        title="",
        description="",
        duration="30",
        duration_unlimited=False,
        start_at="",
        end_at="",
    )


@quiz_bp.post("/quiz/create")
@role_required("lecturer")
def submit_create_quiz():
    """Validate and create a draft quiz."""

    title = request.form.get("title", "")
    description = request.form.get("description", "")
    duration = request.form.get("duration", "")
    duration_unlimited = request.form.get("duration_unlimited") == "yes"
    start_at = request.form.get("start_at", "")
    end_at = request.form.get("end_at", "")

    try:
        quiz_id = create_new_quiz(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            title,
            duration,
            description,
            start_at,
            end_at,
            duration_unlimited,
        )

    except InvalidQuiz as error:
        return (
            render_template(
                "create_quiz.html",
                error=str(error),
                title=title,
                description=description,
                duration=duration,
                duration_unlimited=duration_unlimited,
                start_at=start_at,
                end_at=end_at,
            ),
            422,
        )

    flash("Quiz created successfully.", "success")
    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))


@quiz_bp.get("/quiz/<int:quiz_id>/questions")
@role_required("lecturer")
def questions_page(quiz_id: int):
    try:
        get_questions_page_data(
            current_app.config["DATABASE_PATH"],
            session["user_id"],
            quiz_id,
        )

    except QuestionError as error:
        return render_error(
            error.status_code,
            error.message,
        )

    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))


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
        return render_error(
            error.status_code,
            error.message,
        )

    except InvalidQuestion as error:
        try:
            data = get_quiz_publish_details(
                db_path,
                session["user_id"],
                quiz_id,
            )

        except (QuestionError, QuizServiceError) as page_error:
            return render_error(
                page_error.status_code,
                page_error.message,
            )

        return (
            render_template(
                "publish_quiz.html",
                **data,
                messages=error.messages,
                form=form,
                choice_labels=CHOICE_LABELS,
                max_points=MAX_POINTS,
                schedule_error=None,
                show_add_form=True,
            ),
            422,
        )

    flash("Question added successfully.", "success")
    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))


@quiz_bp.post("/quiz/<int:quiz_id>/questions/<int:question_id>/edit")
@role_required("lecturer")
def edit_quiz_question(quiz_id: int, question_id: int):
    db_path = current_app.config["DATABASE_PATH"]
    choices = request.form.getlist("choices")
    form = {
        "content": request.form.get("content", ""),
        "choices": (choices + [""] * CHOICE_COUNT)[:CHOICE_COUNT],
        "correct_index": request.form.get("correct_index", ""),
        "points": request.form.get("points", ""),
    }

    try:
        update_question(
            db_path,
            session["user_id"],
            quiz_id,
            question_id,
            form["content"],
            choices,
            form["correct_index"],
            form["points"],
        )
    except QuestionError as error:
        return render_error(error.status_code, error.message)
    except InvalidQuestion as error:
        try:
            data = get_quiz_publish_details(db_path, session["user_id"], quiz_id)
        except (QuestionError, QuizServiceError) as page_error:
            return render_error(page_error.status_code, page_error.message)
        return (
            render_template(
                "publish_quiz.html",
                **data,
                messages=[],
                choice_labels=CHOICE_LABELS,
                max_points=MAX_POINTS,
                schedule_error=None,
                editing_question_id=question_id,
                edit_form=form,
                edit_messages=error.messages,
                show_add_form=False,
            ),
            422,
        )

    flash("Question updated successfully.", "success")
    return redirect(url_for("lecturer.publish_page", quiz_id=quiz_id))
