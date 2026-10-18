import sqlite3


def get_quiz(connection: sqlite3.Connection, quiz_id: int) -> sqlite3.Row | None:
    return connection.execute(
        "SELECT quiz_id, lecturer_id, title, status FROM quiz WHERE quiz_id = ?",
        (quiz_id,),
    ).fetchone()


def list_questions(
    connection: sqlite3.Connection,
    quiz_id: int,
) -> list[dict[str, int | str]]:
    rows = connection.execute(
        """
        SELECT q.question_id, q.content, q.points, q.position,
               (SELECT COUNT(*) FROM choice c WHERE c.question_id = q.question_id)
                   AS choice_count
        FROM question q
        WHERE q.quiz_id = ?
        ORDER BY q.position
        """,
        (quiz_id,),
    )
    return [dict(row) for row in rows]


def next_position(connection: sqlite3.Connection, quiz_id: int) -> int:
    row = connection.execute(
        "SELECT COALESCE(MAX(position), 0) + 1 FROM question WHERE quiz_id = ?",
        (quiz_id,),
    ).fetchone()
    return row[0]


def insert_question(
    connection: sqlite3.Connection,
    quiz_id: int,
    content: str,
    points: int,
    position: int,
) -> int:
    cursor = connection.execute(
        "INSERT INTO question (quiz_id, content, points, position) VALUES (?, ?, ?, ?)",
        (quiz_id, content, points, position),
    )
    return cursor.lastrowid


def insert_choice(
    connection: sqlite3.Connection,
    question_id: int,
    content: str,
    is_correct: bool,
) -> None:
    connection.execute(
        "INSERT INTO choice (question_id, content, is_correct) VALUES (?, ?, ?)",
        (question_id, content, int(is_correct)),
    )
