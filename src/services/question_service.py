import sqlite3
from contextlib import closing
from pathlib import Path

from src import errors
from src.db import get_connection
from src.repositories import question_repository as repo

CHOICE_LABELS = ("A", "B", "C", "D")
CHOICE_COUNT = len(CHOICE_LABELS)
MAX_POINTS = (1 << 63) - 1


class QuestionError(Exception):
    status_code: int
    message: str

    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class InvalidQuestion(Exception):
    messages: list[str]

    def __init__(self, messages: list[str]):
        super().__init__("; ".join(messages))
        self.messages = messages


def _get_owned_quiz(
    connection: sqlite3.Connection,
    lecturer_id: int,
    quiz_id: int,
) -> sqlite3.Row:
    quiz = repo.get_quiz(connection, quiz_id)
    if quiz is None:
        raise QuestionError(404, errors.QUIZ_NOT_FOUND)
    if quiz["lecturer_id"] != lecturer_id:
        raise QuestionError(403, errors.NOT_QUIZ_OWNER)
    return quiz


def _to_int(value: str | None) -> int | None:
    if value is None or not value.isascii() or not value.isdecimal():
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _validate(
    content: str,
    choices: list[str],
    correct_index: str,
    points: str,
) -> tuple[str, list[str], int, int]:
    messages: list[str] = []

    content = content.strip()
    if not content:
        messages.append(errors.QUESTION_CONTENT_REQUIRED)

    choices = [choice.strip() for choice in choices]
    if len(choices) != CHOICE_COUNT or not all(choices):
        messages.append(errors.CHOICES_REQUIRED)

    correct = _to_int(correct_index)
    if correct is None or not 0 <= correct < CHOICE_COUNT:
        messages.append(errors.SELECT_CORRECT_OPTION)

    points_value = _to_int(points)
    if points_value is None or not 1 <= points_value <= MAX_POINTS:
        messages.append(errors.INVALID_POINTS)

    if messages:
        raise InvalidQuestion(messages)
    if correct is None or points_value is None:
        raise RuntimeError("Validated question has invalid numeric fields")

    return content, choices, correct, points_value


def get_questions_page_data(
    db_path: str | Path,
    lecturer_id: int,
    quiz_id: int,
) -> dict[str, object]:
    with closing(get_connection(db_path)) as connection:
        quiz = _get_owned_quiz(connection, lecturer_id, quiz_id)
        questions = repo.list_questions(connection, quiz_id)
        return {
            "quiz": dict(quiz),
            "questions": questions,
            "question_count": len(questions),
        }


def add_question(
    db_path: str | Path,
    lecturer_id: int,
    quiz_id: int,
    content: str,
    choices: list[str],
    correct_index: str,
    points: str,
) -> int:
    with closing(get_connection(db_path)) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            _get_owned_quiz(connection, lecturer_id, quiz_id)

            content, choices, correct, points = _validate(
                content,
                choices,
                correct_index,
                points,
            )

            question_id = repo.insert_question(
                connection,
                quiz_id,
                content,
                points,
                repo.next_position(connection, quiz_id),
            )
            for index, text in enumerate(choices):
                repo.insert_choice(connection, question_id, text, index == correct)

            return question_id
