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