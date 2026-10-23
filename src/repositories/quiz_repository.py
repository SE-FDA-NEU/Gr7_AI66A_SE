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
            q.duration_unlimited,
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
            "duration_unlimited": bool(row[4]),
            "end_at": row[5]
        })
    return quizzes


def get_quiz_by_id(conn, quiz_id: int) -> dict | None:
    """Truy vấn thông tin chi tiết một quiz theo quiz_id."""
    cursor = conn.cursor()
    query = """
        SELECT 
            q.quiz_id, 
            q.lecturer_id, 
            q.title, 
            q.status, 
            q.duration_minutes, 
            q.duration_unlimited,
            q.start_at, 
            q.end_at,
            u.name AS lecturer_name
        FROM quiz q
        JOIN user u ON u.user_id = q.lecturer_id
        WHERE q.quiz_id = ?;
    """
    cursor.execute(query, (quiz_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "quiz_id": row["quiz_id"],
        "lecturer_id": row["lecturer_id"],
        "title": row["title"],
        "status": row["status"],
        "duration_minutes": row["duration_minutes"],
        "duration_unlimited": bool(row["duration_unlimited"]),
        "start_at": row["start_at"],
        "end_at": row["end_at"],
        "lecturer_name": row["lecturer_name"],
    }


def get_quiz_questions_with_choices(conn, quiz_id: int) -> list[dict]:
    """
    Lấy danh sách các câu hỏi và các lựa chọn đi kèm của một quiz.
    Sắp xếp theo position tăng dần.
    """
    cursor = conn.cursor()
    query_q = """
        SELECT question_id, quiz_id, content, points, position
        FROM question
        WHERE quiz_id = ?
        ORDER BY position ASC;
    """
    cursor.execute(query_q, (quiz_id,))
    q_rows = cursor.fetchall()
    
    questions = []
    for q in q_rows:
        q_id = q["question_id"]
        query_c = """
            SELECT choice_id, question_id, content, is_correct
            FROM choice
            WHERE question_id = ?
            ORDER BY choice_id ASC;
        """
        cursor.execute(query_c, (q_id,))
        c_rows = cursor.fetchall()
        
        choices = []
        correct_count = 0
        for c in c_rows:
            is_cor = bool(c["is_correct"])
            if is_cor:
                correct_count += 1
            choices.append({
                "choice_id": c["choice_id"],
                "content": c["content"],
                "is_correct": is_cor,
            })
            
        questions.append({
            "question_id": q["question_id"],
            "quiz_id": q["quiz_id"],
            "content": q["content"],
            "points": q["points"],
            "position": q["position"],
            "choices": choices,
            "correct_count": correct_count,
            "has_valid_correct": correct_count == 1,
            "has_minimum_choices": len(choices) >= 2,
        })
        
    return questions


def update_quiz_status(conn, quiz_id: int, new_status: str) -> None:
    """Cập nhật trạng thái quiz (draft, published, closed)."""
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE quiz SET status = ? WHERE quiz_id = ?",
        (new_status, quiz_id),
    )
    conn.commit()


def list_quizzes_by_lecturer(conn, lecturer_id: int) -> list[dict]:
    """Truy vấn danh sách quiz thuộc sở hữu của một giảng viên."""
    cursor = conn.cursor()
    query = """
        SELECT 
            q.quiz_id, 
            q.title, 
            q.status, 
            q.duration_minutes, 
            q.duration_unlimited,
            q.end_at,
            (SELECT COUNT(*) FROM attempt a WHERE a.quiz_id = q.quiz_id) AS attempt_count
        FROM quiz q
        WHERE q.lecturer_id = ?
        ORDER BY q.quiz_id ASC;
    """
    cursor.execute(query, (lecturer_id,))
    rows = cursor.fetchall()
    
    quizzes = []
    for row in rows:
        quizzes.append({
            "quiz_id": row["quiz_id"],
            "title": row["title"],
            "status": row["status"],
            "duration_minutes": row["duration_minutes"],
            "duration_unlimited": bool(row["duration_unlimited"]),
            "end_at": row["end_at"],
            "attempt_count": row["attempt_count"],
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
            q.duration_unlimited,
            q.start_at,
            q.end_at,
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
            "duration_unlimited": bool(row[3]),
            "start_at": row[4],
            "end_at": row[5],
            "question_count": row[6],
        }
        for row in conn.execute(query)
    ]


def create_quiz(
    conn,
    lecturer_id,
    title,
    duration_minutes,
    description="",
    start_at=None,
    end_at=None,
    duration_unlimited=False,
):
    """Create a new draft quiz with an optional description."""

    cursor = conn.execute(
        """
        INSERT INTO quiz (
            lecturer_id,
            title,
            description,
            status,
            duration_minutes,
            duration_unlimited,
            start_at,
            end_at
        )
        VALUES (?, ?, ?, 'draft', ?, ?, ?, ?)
        """,
        (
            lecturer_id,
            title,
            description,
            duration_minutes,
            int(duration_unlimited),
            start_at,
            end_at,
        ),
    )

    conn.commit()
    return cursor.lastrowid


def update_quiz_schedule(
    conn,
    quiz_id: int,
    start_at: str | None,
    end_at: str | None,
    duration_minutes: int | None = None,
    duration_unlimited: bool | None = None,
) -> None:
    """Save the quiz's UTC schedule and, when provided, its time limit."""
    if duration_minutes is None or duration_unlimited is None:
        conn.execute(
            "UPDATE quiz SET start_at = ?, end_at = ? WHERE quiz_id = ?",
            (start_at, end_at, quiz_id),
        )
    else:
        conn.execute(
            """
            UPDATE quiz
            SET start_at = ?, end_at = ?, duration_minutes = ?, duration_unlimited = ?
            WHERE quiz_id = ?
            """,
            (start_at, end_at, duration_minutes, int(duration_unlimited), quiz_id),
        )
    conn.commit()
