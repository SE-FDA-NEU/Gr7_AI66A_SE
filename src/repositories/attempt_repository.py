"""Database access for quiz attempts and answers."""

import sqlite3


def get_quiz(connection: sqlite3.Connection, quiz_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT quiz_id, title, status, duration_minutes, start_at, end_at
        FROM quiz
        WHERE quiz_id = ?
        """,
        (quiz_id,),
    ).fetchone()


def get_attempt(connection: sqlite3.Connection, attempt_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT attempt_id, student_id, quiz_id, started_at, submitted_at, score
        FROM attempt
        WHERE attempt_id = ?
        """,
        (attempt_id,),
    ).fetchone()


def get_open_attempt(
    connection: sqlite3.Connection,
    student_id: int,
    quiz_id: int,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT attempt_id, student_id, quiz_id, started_at, submitted_at, score
        FROM attempt
        WHERE student_id = ? AND quiz_id = ? AND submitted_at IS NULL
        ORDER BY attempt_id DESC
        LIMIT 1
        """,
        (student_id, quiz_id),
    ).fetchone()


def get_submitted_attempt(
    connection: sqlite3.Connection,
    student_id: int,
    quiz_id: int,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT attempt_id, student_id, quiz_id, started_at, submitted_at, score
        FROM attempt
        WHERE student_id = ? AND quiz_id = ? AND submitted_at IS NOT NULL
        """,
        (student_id, quiz_id),
    ).fetchone()


def list_quiz_attempts(connection: sqlite3.Connection, quiz_id: int) -> list[dict]:
    """Return all student attempts for a quiz, including attempts in progress."""
    rows = connection.execute(
        """
        SELECT
            a.attempt_id,
            a.student_id,
            u.name AS student_name,
            u.email AS student_email,
            a.started_at,
            a.submitted_at,
            a.score,
            COUNT(q.question_id) AS total_questions,
            SUM(CASE WHEN selected_choice.is_correct = 1 THEN 1 ELSE 0 END)
                AS correct_count
        FROM attempt a
        JOIN user u ON u.user_id = a.student_id
        LEFT JOIN question q ON q.quiz_id = a.quiz_id
        LEFT JOIN answer ans
            ON ans.attempt_id = a.attempt_id AND ans.question_id = q.question_id
        LEFT JOIN choice selected_choice ON selected_choice.choice_id = ans.choice_id
        WHERE a.quiz_id = ?
        GROUP BY a.attempt_id
        ORDER BY a.started_at DESC, a.attempt_id DESC
        """,
        (quiz_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_attempt_answers(
    connection: sqlite3.Connection,
    attempt_id: int,
) -> list[dict]:
    """Return each question, the student's answer, and its correct answer."""
    rows = connection.execute(
        """
        SELECT
            q.question_id,
            q.position,
            q.content,
            q.points,
            ans.choice_id AS selected_choice_id,
            selected_choice.content AS selected_choice,
            correct_choice.content AS correct_choice,
            CASE
                WHEN ans.choice_id IS NULL THEN NULL
                WHEN selected_choice.is_correct = 1 THEN 1
                ELSE 0
            END AS is_correct
        FROM attempt a
        JOIN question q ON q.quiz_id = a.quiz_id
        LEFT JOIN answer ans
            ON ans.attempt_id = a.attempt_id AND ans.question_id = q.question_id
        LEFT JOIN choice selected_choice ON selected_choice.choice_id = ans.choice_id
        LEFT JOIN choice correct_choice
            ON correct_choice.question_id = q.question_id
            AND correct_choice.is_correct = 1
        WHERE a.attempt_id = ?
        ORDER BY q.position
        """,
        (attempt_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def create_attempt(
    connection: sqlite3.Connection,
    student_id: int,
    quiz_id: int,
    started_at: str,
) -> int:
    cursor = connection.execute(
        "INSERT INTO attempt (student_id, quiz_id, started_at) VALUES (?, ?, ?)",
        (student_id, quiz_id, started_at),
    )
    return cursor.lastrowid


def list_questions_with_choices(
    connection: sqlite3.Connection,
    quiz_id: int,
) -> list[dict]:
    """Return the quiz's questions in position order, each with its choices."""
    questions = [
        {
            "question_id": row["question_id"],
            "content": row["content"],
            "points": row["points"],
            "position": row["position"],
            "choices": [],
        }
        for row in connection.execute(
            """
            SELECT question_id, content, points, position
            FROM question
            WHERE quiz_id = ?
            ORDER BY position
            """,
            (quiz_id,),
        )
    ]
    by_id = {question["question_id"]: question for question in questions}

    for row in connection.execute(
        """
        SELECT c.choice_id, c.question_id, c.content
        FROM choice c
        JOIN question q ON q.question_id = c.question_id
        WHERE q.quiz_id = ?
        ORDER BY c.choice_id
        """,
        (quiz_id,),
    ):
        by_id[row["question_id"]]["choices"].append(
            {"choice_id": row["choice_id"], "content": row["content"]}
        )

    return questions


def get_selected_choices(
    connection: sqlite3.Connection,
    attempt_id: int,
) -> dict[int, int | None]:
    return {
        row["question_id"]: row["choice_id"]
        for row in connection.execute(
            "SELECT question_id, choice_id FROM answer WHERE attempt_id = ?",
            (attempt_id,),
        )
    }


def choice_belongs_to_question(
    connection: sqlite3.Connection,
    choice_id: int,
    question_id: int,
    quiz_id: int,
) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM choice c
        JOIN question q ON q.question_id = c.question_id
        WHERE c.choice_id = ? AND c.question_id = ? AND q.quiz_id = ?
        """,
        (choice_id, question_id, quiz_id),
    ).fetchone()
    return row is not None


def upsert_answer(
    connection: sqlite3.Connection,
    attempt_id: int,
    question_id: int,
    choice_id: int,
) -> None:
    connection.execute(
        """
        INSERT INTO answer (attempt_id, question_id, choice_id)
        VALUES (?, ?, ?)
        ON CONFLICT(attempt_id, question_id) DO UPDATE SET choice_id = excluded.choice_id
        """,
        (attempt_id, question_id, choice_id),
    )


def count_correct_answers(connection: sqlite3.Connection, attempt_id: int) -> int:
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM answer a
        JOIN choice c ON c.choice_id = a.choice_id
        WHERE a.attempt_id = ? AND c.is_correct = 1
        """,
        (attempt_id,),
    ).fetchone()[0]


def mark_submitted(
    connection: sqlite3.Connection,
    attempt_id: int,
    submitted_at: str,
    score: float,
) -> int:
    """Submit an open attempt; returns 0 when it was already submitted (BR6)."""
    cursor = connection.execute(
        """
        UPDATE attempt
        SET submitted_at = ?, score = ?
        WHERE attempt_id = ? AND submitted_at IS NULL
        """,
        (submitted_at, score, attempt_id),
    )
    return cursor.rowcount
