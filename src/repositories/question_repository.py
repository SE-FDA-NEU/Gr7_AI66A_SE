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


def get_question(
    connection: sqlite3.Connection,
    quiz_id: int,
    question_id: int,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT question_id
        FROM question
        WHERE quiz_id = ? AND question_id = ?
        """,
        (quiz_id, question_id),
    ).fetchone()


def update_question(
    connection: sqlite3.Connection,
    question_id: int,
    content: str,
    points: int,
    choices: list[str],
    correct_index: int,
) -> None:
    connection.execute(
        "UPDATE question SET content = ?, points = ? WHERE question_id = ?",
        (content, points, question_id),
    )
    existing_choices = connection.execute(
        "SELECT choice_id FROM choice WHERE question_id = ? ORDER BY choice_id",
        (question_id,),
    ).fetchall()
    connection.execute(
        "UPDATE choice SET is_correct = 0 WHERE question_id = ?",
        (question_id,),
    )

    for index, text in enumerate(choices):
        is_correct = int(index == correct_index)
        if index < len(existing_choices):
            connection.execute(
                """
                UPDATE choice
                SET content = ?, is_correct = ?
                WHERE choice_id = ?
                """,
                (text, is_correct, existing_choices[index]["choice_id"]),
            )
        else:
            insert_choice(connection, question_id, text, bool(is_correct))

    for extra_choice in existing_choices[len(choices):]:
        connection.execute(
            "UPDATE choice SET is_correct = 0 WHERE choice_id = ?",
            (extra_choice["choice_id"],),
        )
