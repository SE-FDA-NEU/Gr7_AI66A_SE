def list_published_quizzes(conn):
    """
    Truy vấn danh sách các quiz có status = 'published'
    Trả về danh sách dạng dict gồm: quiz_id, title, lecturer_name, duration_minutes, end_at
    """
    cursor = conn.cursor()
    query = """
        SELECT 
            q.quiz_id, 
            q.title, 
            u.name AS lecturer_name, 
            q.duration_minutes, 
            q.end_at 
        FROM quiz q 
        JOIN user u ON u.user_id = q.lecturer_id 
        WHERE q.status = 'published' 
        ORDER BY q.end_at ASC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    quizzes = []
    for row in rows:
        quizzes.append({
            "quiz_id": row[0],
            "title": row[1],
            "lecturer_name": row[2],
            "duration_minutes": row[3],
            "end_at": row[4]
        })
    return quizzes


def list_published_quizzes_with_question_count(conn):
    """
    Truy vấn các quiz có status = 'published' kèm số câu hỏi của mỗi quiz
    Trả về danh sách dạng dict gồm: quiz_id, title, duration_minutes, question_count
    """
    query = """
        SELECT
            q.quiz_id,
            q.title,
            q.duration_minutes,
            COUNT(qu.question_id) AS question_count
        FROM quiz q
        LEFT JOIN question qu ON qu.quiz_id = q.quiz_id
        WHERE q.status = 'published'
        GROUP BY q.quiz_id
        ORDER BY q.end_at ASC;
    """
    return [
        {
            "quiz_id": row[0],
            "title": row[1],
            "duration_minutes": row[2],
            "question_count": row[3],
        }
        for row in conn.execute(query)
    ]


def create_quiz(
    conn,
    lecturer_id,
    title,
    duration_minutes,
    description="",
):
    """Create a new draft quiz with an optional description."""

    cursor = conn.execute(
        """
        INSERT INTO quiz (
            lecturer_id,
            title,
            description,
            status,
            duration_minutes
        )
        VALUES (?, ?, ?, 'draft', ?)
        """,
        (
            lecturer_id,
            title,
            description,
            duration_minutes,
        ),
    )

    conn.commit()
    return cursor.lastrowid
