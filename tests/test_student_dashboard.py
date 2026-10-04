from src.app import create_app
from src.db import get_connection
from src.init_db import init_db


def test_student_dashboard_shows_published_quizzes(tmp_path):
    db_path = tmp_path / "minilms.db"
    init_db(db_path)

    with get_connection(db_path) as connection:
        connection.execute(
            "UPDATE quiz SET title = ? WHERE quiz_id = 1",
            ("Updated title from database",),
        )

    app = create_app({"TESTING": True, "DATABASE_PATH": db_path})
    response = app.test_client().get("/student/dashboard")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Updated title from database" in html
    assert html.count("<tr>") == 13
    assert html.count("<td>") == 48
    assert "Advanced Analytics" not in html
    assert "Quiz Security Review" not in html
    assert "Final Practice Quiz" not in html
