from pathlib import Path

from src.db import get_connection
from src.repositories.quiz_repository import list_published_quizzes


def get_student_dashboard_data(db_path: str | Path):
    """
    Lấy danh sách quiz cho màn hình Dashboard sinh viên
    """
    conn = get_connection(db_path)
    try:
        quizzes = list_published_quizzes(conn)
        return quizzes
    finally:
        conn.close()