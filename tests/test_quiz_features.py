import pytest
from src.app import create_app
from src.db import get_connection
from src.init_db import init_db

QUIZ_ID = 1
STATS_URL = f'/lecturer/quiz/{QUIZ_ID}/statistics'


@pytest.fixture
def context(tmp_path):
    db = tmp_path / 'us10.db'
    init_db(db)
    app = create_app({'TESTING': True, 'DATABASE_PATH': db})
    return app, db


def login(client, email='ngan.lecturer@example.edu'):
    result = client.post('/login', data={'email': email, 'password': 'MiniLMS2026!'})
    assert result.status_code == 302


def seed_submissions(db, scores):
    # Seed students individually to obey the schema's unique attempt/student constraints.
    with get_connection(db) as conn:
        for idx, score in enumerate(scores):
            cursor = conn.execute(
                'INSERT INTO user (name, email, password_hash, role) VALUES (?, ?, ?, ?)',
                (f'Stats student {idx}', f'us10-student-{idx}@example.edu', 'unused', 'student'),
            )
            student_id = cursor.lastrowid
            conn.execute(
                "INSERT INTO attempt (student_id, quiz_id, started_at, submitted_at, score) "
                "VALUES (?, ?, '2026-10-20T09:00:00', '2026-10-20T09:15:00', ?)",
                (student_id, QUIZ_ID, score),
            )


def test_us10_ac1_statistics_show_20_submitted_attempts(context):
    app, db = context
    seed_submissions(db, [0.8] * 20)
    client = app.test_client()
    login(client)
    response = client.get(STATS_URL)
    assert response.status_code == 200
    assert '20' in response.get_data(as_text=True)


def test_us10_ac2_statistics_show_average_80_percent(context):
    app, db = context
    seed_submissions(db, [0.6, 0.8, 1.0])
    client = app.test_client()
    login(client)
    response = client.get(STATS_URL)
    assert response.status_code == 200
    assert '80%' in response.get_data(as_text=True)


def test_us10_ac3_question_correct_rate_is_75_percent(context):
    app, db = context
    seed_submissions(db, [1.0] * 15 + [0.0] * 5)
    with get_connection(db) as conn:
        question_id = conn.execute('SELECT question_id FROM question WHERE quiz_id = ? LIMIT 1', (QUIZ_ID,)).fetchone()[0]
        correct = conn.execute('SELECT choice_id FROM choice WHERE question_id = ? AND is_correct = 1', (question_id,)).fetchone()[0]
        wrong = conn.execute('SELECT choice_id FROM choice WHERE question_id = ? AND is_correct = 0 LIMIT 1', (question_id,)).fetchone()[0]
        ids = [r[0] for r in conn.execute('SELECT attempt_id FROM attempt WHERE quiz_id = ? ORDER BY attempt_id', (QUIZ_ID,)).fetchall()]
        for index, attempt_id in enumerate(ids):
            conn.execute('INSERT INTO answer (attempt_id, question_id, choice_id) VALUES (?, ?, ?)', (attempt_id, question_id, correct if index < 15 else wrong))
    client = app.test_client()
    login(client)
    response = client.get(STATS_URL)
    assert response.status_code == 200
    assert '75%' in response.get_data(as_text=True)


def test_us10_ac4_other_lecturer_cannot_see_statistics(context):
    app, _ = context
    client = app.test_client()
    login(client, 'nam.lecturer@example.edu')
    response = client.get(STATS_URL)
    assert response.status_code == 403


def test_us10_boundary_no_submissions_no_division_by_zero(context):
    app, _ = context
    client = app.test_client()
    login(client)
    response = client.get(STATS_URL)
    assert response.status_code == 200
