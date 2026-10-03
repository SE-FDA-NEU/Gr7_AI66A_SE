import os
import sqlite3

# Đường dẫn lưu CSDL
DB_DIR = "data"
DB_PATH = os.path.join(DB_DIR, "minilms.db")

def init_database():
    # 1. Tạo thư mục data 
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR)

    # 2. Kết nối tới SQLite Database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Bật tính năng khóa ngoại
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 3. Xóa các bảng cũ nếu có
    cursor.execute("DROP TABLE IF EXISTS answers;")
    cursor.execute("DROP TABLE IF EXISTS attempts;")
    cursor.execute("DROP TABLE IF EXISTS questions;")
    cursor.execute("DROP TABLE IF EXISTS quizzes;")
    cursor.execute("DROP TABLE IF EXISTS users;")
    print("[INFO] Dropped existing tables if any.")

    # 4. Tạo cấu trúc Bảng
    cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'lecturer'))
    );
    """)

    cursor.execute("""
    CREATE TABLE quizzes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        lecturer_id INTEGER NOT NULL,
        duration_minutes INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'published' CHECK(status IN ('draft', 'published', 'archived')),
        FOREIGN KEY (lecturer_id) REFERENCES users(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        quiz_id INTEGER NOT NULL,
        content TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        correct_option TEXT NOT NULL,
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        quiz_id INTEGER NOT NULL,
        score REAL,
        submitted_at DATETIME,
        FOREIGN KEY (student_id) REFERENCES users(id),
        FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
    );
    """)

    cursor.execute("""
    CREATE TABLE answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attempt_id INTEGER NOT NULL,
        question_id INTEGER NOT NULL,
        selected_option TEXT NOT NULL,
        FOREIGN KEY (attempt_id) REFERENCES attempts(id),
        FOREIGN KEY (question_id) REFERENCES questions(id)
    );
    """)
    print("[INFO] Created tables: users, quizzes, questions, attempts, answers.")

    # 5. Seed dữ liệu mẫu

    # Seed Users 
    users = [
        ('lecturer_hung', 'pass123', 'lecturer'),
        ('student_khang', 'pass123', 'student'),
        ('student_an', 'pass123', 'student'),
        ('student_binh', 'pass123', 'student'),
        ('student_cuong', 'pass123', 'student')
    ]
    cursor.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?);", users)
    print(f"[INFO] Successfully seeded {len(users)} users (1 Lecturer, 4 Students).")

    # Seed Quizzes
    quizzes = [
        ("Python Programming Basics", 1, 30, "published"),
        ("Flask Framework Essentials", 1, 45, "published"),
        ("Database Systems & SQL Constraints", 1, 60, "published"),
        ("HTML5 & CSS3 Fundamentals", 1, 30, "published"),
        ("JavaScript Async/Await Overview", 1, 40, "published"),
        ("Git & Version Control Workflows", 1, 20, "published"),
        ("Software Engineering & Agile Methodologies", 1, 50, "published"),
        ("RESTful API Design & Best Practices", 1, 45, "published"),
        ("Unit Testing with PyTest", 1, 30, "published"),
        ("Data Structures: Trees & Graphs", 1, 60, "published"),
        ("Web Security: OWASP Top 10", 1, 40, "published"),
        ("DevOps & CI/CD Pipelines Basics", 1, 30, "published")
    ]
    cursor.executemany("INSERT INTO quizzes (title, lecturer_id, duration_minutes, status) VALUES (?, ?, ?, ?);", quizzes)
    print(f"[INFO] Successfully seeded {len(quizzes)} quizzes.")

    # Seed Questions
    questions = []
    for quiz_id in range(1, 13):
        questions.append((
            quiz_id,
            f"Question 1 for Quiz {quiz_id}: What is the core concept of this topic?",
            "Option A", "Option B", "Option C", "Option D", "A"
        ))
        questions.append((
            quiz_id,
            f"Question 2 for Quiz {quiz_id}: Which of the following is correct?",
            "Option A", "Option B", "Option C", "Option D", "B"
        ))
    cursor.executemany("INSERT INTO questions (quiz_id, content, option_a, option_b, option_c, option_d, correct_option) VALUES (?, ?, ?, ?, ?, ?, ?);", questions)
    print(f"[INFO] Successfully seeded {len(questions)} quiz questions.")

    # 6. Commit và đóng kết nối
    conn.commit()
    
    total_rows = len(users) + len(quizzes) + len(questions)
    conn.close()

    print(f"[SUCCESS] Database initialized at {DB_PATH} with {total_rows} total rows.")

if __name__ == "__main__":
    init_database()