
from pathlib import Path

from src import errors
from src.db import get_connection
from src.repositories.quiz_repository import (
    get_quiz_by_id,
    get_quiz_questions_with_choices,
    list_published_quizzes,
    list_quizzes_by_lecturer,
    update_quiz_status,
)


class QuizServiceError(Exception):
    """Custom exception for quiz operations and business rule violations."""

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
from src.repositories.attempt_repository import get_open_attempt, get_submitted_attempt
from src.repositories.quiz_repository import (
    create_quiz,
    list_published_quizzes,
    list_published_quizzes_with_question_count,
)


# ==========================================
# STUDENT DASHBOARD
# ==========================================

def get_student_dashboard_data(db_path: str | Path):
    """
    Lấy danh sách quiz đã publish
    cho màn hình Dashboard sinh viên.
    """
    conn = get_connection(db_path)

    try:
        quizzes = list_published_quizzes(conn)
        return quizzes
    finally:
        conn.close()


def get_lecturer_dashboard_data(db_path: str | Path, lecturer_id: int):
    """Lấy danh sách quiz thuộc về giảng viên đang đăng nhập."""
    conn = get_connection(db_path)
    try:
        quizzes = list_quizzes_by_lecturer(conn, lecturer_id)
        return quizzes
    finally:
        conn.close()


def get_quiz_publish_details(db_path: str | Path, lecturer_id: int, quiz_id: int) -> dict:
    """
    Lấy thông tin quiz và danh sách câu hỏi để hiển thị trang /lecturer/quiz/:id/publish.
    Kiểm tra quyền sở hữu BR2: nếu quiz thuộc giảng viên khác thì báo lỗi 403.
    """
    conn = get_connection(db_path)
    try:
        quiz = get_quiz_by_id(conn, quiz_id)
        if not quiz:
            raise QuizServiceError(404, errors.QUIZ_NOT_FOUND)

        # BR2: Không phải chủ quiz thì chặn
        if quiz["lecturer_id"] != lecturer_id:
            raise QuizServiceError(403, errors.NOT_QUIZ_OWNER)

        questions = get_quiz_questions_with_choices(conn, quiz_id)

        # Kiểm tra tính hợp lệ theo BR3
        is_publishable = True
        validation_error = None

        if len(questions) < 1:
            is_publishable = False
            validation_error = errors.QUIZ_NO_QUESTIONS
        else:
            for q in questions:
                if not q["has_minimum_choices"]:
                    is_publishable = False
                    validation_error = errors.quiz_question_insufficient_choices(q["position"])
                    break
                if not q["has_valid_correct"]:
                    is_publishable = False
                    validation_error = errors.quiz_question_missing_correct_choice(q["position"])
                    break

        return {
            "quiz": quiz,
            "questions": questions,
            "is_publishable": is_publishable,
            "validation_error": validation_error,
        }
    finally:
        conn.close()


def publish_quiz(db_path: str | Path, lecturer_id: int, quiz_id: int) -> dict:
    """
    Publish một bài quiz (US04, BR2, BR3):
    - Đổi trạng thái sang 'published'.
    - Báo 403 nếu không phải chủ quiz (BR2).
    - Báo 409 nếu quiz đã được publish trước đó.
    - Báo 422 nếu quiz không đủ điều kiện (BR3: 0 câu hỏi hoặc câu hỏi chưa có đáp án đúng).
    """
    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        quiz = get_quiz_by_id(conn, quiz_id)
        if not quiz:
            conn.rollback()
            raise QuizServiceError(404, errors.QUIZ_NOT_FOUND)

        # BR2: Chỉ chủ sở hữu quiz mới được publish
        if quiz["lecturer_id"] != lecturer_id:
            conn.rollback()
            raise QuizServiceError(403, errors.NOT_QUIZ_OWNER)

        if quiz["status"] == "published":
            conn.rollback()
            raise QuizServiceError(409, errors.QUIZ_ALREADY_PUBLISHED)

        if quiz["status"] == "closed":
            conn.rollback()
            raise QuizServiceError(400, errors.QUIZ_CANNOT_REPUBLISH_CLOSED)

        # BR3: Kiểm tra quiz có ít nhất 1 câu hỏi
        questions = get_quiz_questions_with_choices(conn, quiz_id)
        if len(questions) < 1:
            conn.rollback()
            raise QuizServiceError(422, errors.QUIZ_NO_QUESTIONS)

        # BR3: Mỗi câu hỏi phải có ít nhất 2 lựa chọn và đúng 1 đáp án đúng
        for q in questions:
            if not q["has_minimum_choices"]:
                conn.rollback()
                raise QuizServiceError(422, errors.quiz_question_insufficient_choices(q["position"]))
            if not q["has_valid_correct"]:
                conn.rollback()
                raise QuizServiceError(422, errors.quiz_question_missing_correct_choice(q["position"]))

        update_quiz_status(conn, quiz_id, "published")
        conn.commit()

        updated_quiz = get_quiz_by_id(conn, quiz_id)
        return updated_quiz
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def close_quiz(db_path: str | Path, lecturer_id: int, quiz_id: int) -> dict:
    """
    Đóng một bài quiz (US04, BR2):
    - Đổi trạng thái sang 'closed'.
    - Báo 403 nếu không phải chủ quiz (BR2).
    - Báo 400 nếu quiz đang ở trạng thái 'draft' (chưa từng publish).
    - Báo 409 nếu quiz đã ở trạng thái 'closed'.
    """
    conn = get_connection(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        quiz = get_quiz_by_id(conn, quiz_id)
        if not quiz:
            conn.rollback()
            raise QuizServiceError(404, errors.QUIZ_NOT_FOUND)

        # BR2: Chỉ chủ sở hữu quiz mới được đóng
        if quiz["lecturer_id"] != lecturer_id:
            conn.rollback()
            raise QuizServiceError(403, errors.NOT_QUIZ_OWNER)

        # Kiểm tra trạng thái: chỉ quiz đang 'published' mới được đóng
        if quiz["status"] == "draft":
            conn.rollback()
            raise QuizServiceError(400, errors.QUIZ_DRAFT_CANNOT_BE_CLOSED)

        if quiz["status"] == "closed":
            conn.rollback()
            raise QuizServiceError(409, errors.QUIZ_ALREADY_CLOSED)

        update_quiz_status(conn, quiz_id, "closed")
        conn.commit()

        updated_quiz = get_quiz_by_id(conn, quiz_id)
        return updated_quiz
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
def get_student_quiz_statuses(db_path: str | Path, student_id: int):
    """
    Lấy danh sách quiz đã publish kèm trạng thái sinh viên:
    - submitted
    - in_progress
    - not_started
    """
    conn = get_connection(db_path)

    try:
        quizzes = list_published_quizzes_with_question_count(conn)

        for quiz in quizzes:
            quiz_id = quiz["quiz_id"]

            if get_submitted_attempt(
                conn, student_id, quiz_id
            ) is not None:
                quiz["status"] = "submitted"

            elif get_open_attempt(
                conn, student_id, quiz_id
            ) is not None:
                quiz["status"] = "in_progress"

            else:
                quiz["status"] = "not_started"

        return quizzes

    finally:
        conn.close()


# ==========================================
# US02 - CREATE QUIZ
# ==========================================

class InvalidQuiz(Exception):
    """Raised when quiz creation data is invalid."""


def create_new_quiz(
    db_path: str | Path,
    lecturer_id: int,
    title: str,
    duration: str,
    description: str = "",
) -> int:
    """
    Validate input and create a draft quiz.

    - Title is required.
    - Duration must be a positive integer.
    - Description is optional.
    - New quiz status is draft.
    """

    title = title.strip()
    description = description.strip()

    if not title:
        raise InvalidQuiz("Quiz title is required.")

    try:
        duration_minutes = int(duration)
    except (ValueError, TypeError):
        raise InvalidQuiz(
            "Duration must be a positive number."
        )

    if duration_minutes <= 0:
        raise InvalidQuiz(
            "Duration must be a positive number."
        )

    conn = get_connection(db_path)

    try:
        quiz_id = create_quiz(
            conn,
            lecturer_id,
            title,
            duration_minutes,
            description,
        )

        return quiz_id

    finally:
        conn.close()
