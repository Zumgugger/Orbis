"""
Smoke tests for todo CRUD operations
"""
from datetime import date, timedelta

from database import Todo, User, db


def test_todo_list_page_loads(authenticated_client):
    """Test that todo list page loads"""
    response = authenticated_client.get("/todos/")
    assert response.status_code == 200
    assert b"Todos" in response.data or b"To-Do" in response.data


def test_create_todo(authenticated_client, app, test_user):
    """Test creating a new todo"""
    response = authenticated_client.post(
        "/todos/create",
        data={
            "title": "New Test Todo",
            "description": "Test description",
            "priority": "high",
            "due_date": str(date.today() + timedelta(days=1)),
            "status": "pending",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Verify todo was created in database
    with app.app_context():
        todo = Todo.query.filter_by(title="New Test Todo", user_id=test_user).first()
        assert todo is not None
        assert todo.description == "Test description"
        assert todo.priority == "high"
        assert todo.status == "pending"


def test_toggle_todo_status(authenticated_client, app, sample_todo):
    """Test toggling todo status between pending and completed"""
    # Toggle to completed
    response = authenticated_client.post(
        f"/todos/{sample_todo}/toggle", follow_redirects=True
    )
    assert response.status_code == 200

    with app.app_context():
        todo = db.session.get(Todo, sample_todo)
        assert todo.status == "completed"

    # Toggle back to pending
    response = authenticated_client.post(
        f"/todos/{sample_todo}/toggle", follow_redirects=True
    )
    assert response.status_code == 200

    with app.app_context():
        todo = db.session.get(Todo, sample_todo)
        assert todo.status == "pending"


def test_edit_todo(authenticated_client, app, sample_todo):
    """Test editing an existing todo"""
    response = authenticated_client.post(
        f"/todos/{sample_todo}/edit",
        data={
            "title": "Updated Todo Title",
            "description": "Updated description",
            "priority": "low",
            "due_date": str(date.today() + timedelta(days=2)),
            "status": "in_progress",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        todo = db.session.get(Todo, sample_todo)
        assert todo.title == "Updated Todo Title"
        assert todo.description == "Updated description"
        assert todo.priority == "low"
        assert todo.status == "in_progress"


def test_delete_todo(authenticated_client, app, sample_todo):
    """Test deleting a todo"""
    response = authenticated_client.post(
        f"/todos/{sample_todo}/delete", follow_redirects=True
    )
    assert response.status_code == 200

    with app.app_context():
        todo = db.session.get(Todo, sample_todo)
        assert todo is None


def test_cannot_access_other_user_todo(authenticated_client, app):
    """Test that users cannot access todos from other users"""
    # Create a todo for a different user
    with app.app_context():
        other_user = User(
            google_id="other_google_456",
            email="other@example.com",
            name="Other User",
            profile_pic="https://example.com/other.jpg",
        )
        db.session.add(other_user)
        db.session.commit()

        other_todo = Todo(
            user_id=other_user.id, title="Other User Todo", status="pending"
        )
        db.session.add(other_todo)
        db.session.commit()
        other_todo_id = other_todo.id

    # Try to access other user's todo
    response = authenticated_client.get(f"/todos/{other_todo_id}/edit")
    assert response.status_code in [403, 404]  # Should be forbidden or not found
