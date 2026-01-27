"""
Tests for External API endpoints
"""

import pytest

from extensions import db
from models import ApiKey, Note, NoteType, Todo, User


@pytest.fixture
def api_user(app, client):
    """Create a test user with an API key"""
    with app.app_context():
        # Create a note type first
        user = User.query.first()
        if not user:
            user = User(
                google_id="test_api_user",
                email="apitest@example.com",
                name="API Test User",
                role="user",
            )
            db.session.add(user)
            db.session.flush()

        # Ensure note types exist
        for note_type_name in [
            "journal",
            "health",
            "learned",
            "instructions",
            "support",
        ]:
            if not NoteType.query.filter_by(
                user_id=user.id, name=note_type_name
            ).first():
                note_type = NoteType(user_id=user.id, name=note_type_name)
                db.session.add(note_type)

        db.session.commit()

        # Create API key
        plain_key, _ = ApiKey.create_for_user(user.id)
        return {"user": user, "key": plain_key, "user_id": user.id}


class TestApiAuthentication:
    """Test API authentication"""

    def test_missing_api_key(self, client):
        """Test request without API key"""
        response = client.post("/api/v1/todos", json={"title": "Test"})
        assert response.status_code == 401
        data = response.get_json()
        assert "error" in data

    def test_invalid_api_key(self, client):
        """Test request with invalid API key"""
        response = client.post(
            "/api/v1/todos",
            json={"title": "Test"},
            headers={"Authorization": "Bearer invalid_key"},
        )
        assert response.status_code == 401

    def test_invalid_format(self, client):
        """Test request with invalid Authorization header format"""
        response = client.post(
            "/api/v1/todos",
            json={"title": "Test"},
            headers={"Authorization": "Invalid format"},
        )
        assert response.status_code == 401


class TestCreateTodo:
    """Test TODO creation endpoint"""

    def test_create_todo_minimal(self, client, api_user):
        """Test creating a todo with minimal fields"""
        response = client.post(
            "/api/v1/todos",
            json={
                "title": "Test Todo",
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["todo"]["title"] == "Test Todo"
        assert "id" in data["todo"]

    def test_create_todo_full(self, client, api_user):
        """Test creating a todo with all fields"""
        from time_utils import today_local

        today = today_local().isoformat()
        response = client.post(
            "/api/v1/todos",
            json={
                "title": "Review registration: user@example.com",
                "source_app": "AppX",
                "due_date": today,
                "priority": 3,
                "tags": ["urgent", "registrations"],
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert data["todo"]["title"] == "Review registration: user@example.com"
        assert data["todo"]["priority"] == "high"

        # Verify todo was created in database
        with client.application.app_context():
            todo = Todo.query.filter_by(
                title="Review registration: user@example.com"
            ).first()
            assert todo is not None
            assert todo.priority == "high"
            assert len(todo.tags) == 2

    def test_create_todo_missing_title(self, client, api_user):
        """Test creating a todo without title"""
        response = client.post(
            "/api/v1/todos",
            json={"source_app": "TestApp"},
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "title" in data["details"]

    def test_create_todo_missing_source_app(self, client, api_user):
        """Test creating a todo without source_app"""
        response = client.post(
            "/api/v1/todos",
            json={"title": "Test"},
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "source_app" in data["details"]

    def test_create_todo_invalid_priority(self, client, api_user):
        """Test creating a todo with invalid priority"""
        response = client.post(
            "/api/v1/todos",
            json={
                "title": "Test",
                "source_app": "TestApp",
                "priority": 5,
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "priority" in data["details"]

    def test_create_todo_invalid_date(self, client, api_user):
        """Test creating a todo with invalid date format"""
        response = client.post(
            "/api/v1/todos",
            json={
                "title": "Test",
                "source_app": "TestApp",
                "due_date": "invalid-date",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "due_date" in data["details"]

    def test_create_todo_title_too_long(self, client, api_user):
        """Test creating a todo with title > 200 chars"""
        long_title = "x" * 201
        response = client.post(
            "/api/v1/todos",
            json={
                "title": long_title,
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400

    def test_rate_limit_headers(self, client, api_user):
        """Test that rate limit headers are returned"""
        response = client.post(
            "/api/v1/todos",
            json={
                "title": "Test",
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert "X-RateLimit-Limit" in response.headers
        assert response.headers["X-RateLimit-Limit"] == "10"
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers


class TestCreateNote:
    """Test NOTE creation endpoint"""

    def test_create_note_minimal(self, client, api_user):
        """Test creating a note with minimal fields"""
        response = client.post(
            "/api/v1/notes",
            json={
                "title": "Test Note",
                "type": "journal",
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "id" in data["note"]
        assert data["note"]["type"] == "journal"

    def test_create_note_with_content(self, client, api_user):
        """Test creating a note with content"""
        response = client.post(
            "/api/v1/notes",
            json={
                "title": "Support Request",
                "type": "support",
                "content": "Customer needs help with login",
                "source_app": "SupportDesk",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True

        # Verify note was created with content
        with client.application.app_context():
            note = Note.query.filter_by(title=data["note"]["title"]).first()
            assert note is not None
            assert "Customer needs help with login" in note.content
            assert "SupportDesk" in note.content

    def test_create_note_missing_title(self, client, api_user):
        """Test creating a note without title"""
        response = client.post(
            "/api/v1/notes",
            json={
                "type": "journal",
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "title" in data["details"]

    def test_create_note_missing_type(self, client, api_user):
        """Test creating a note without type"""
        response = client.post(
            "/api/v1/notes",
            json={
                "title": "Test",
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "type" in data["details"]

    def test_create_note_invalid_type(self, client, api_user):
        """Test creating a note with invalid type"""
        response = client.post(
            "/api/v1/notes",
            json={
                "title": "Test",
                "type": "nonexistent",
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "type" in data["details"]

    def test_create_note_missing_source_app(self, client, api_user):
        """Test creating a note without source_app"""
        response = client.post(
            "/api/v1/notes",
            json={
                "title": "Test",
                "type": "journal",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "source_app" in data["details"]


class TestRateLimiting:
    """Test rate limiting functionality"""

    def test_rate_limit_exceeded(self, client, api_user):
        """Test that rate limiting works after 10 requests"""
        # Make 10 requests
        for i in range(10):
            response = client.post(
                "/api/v1/todos",
                json={
                    "title": f"Test {i}",
                    "source_app": "TestApp",
                },
                headers={"Authorization": f"Bearer {api_user['key']}"},
            )
            assert response.status_code == 201

        # 11th request should be rate limited
        response = client.post(
            "/api/v1/todos",
            json={
                "title": "Test 11",
                "source_app": "TestApp",
            },
            headers={"Authorization": f"Bearer {api_user['key']}"},
        )
        assert response.status_code == 429
        data = response.get_json()
        assert "rate limit" in data["error"].lower()
        assert "retry_after" in data

    def test_rate_limit_counter_decreases(self, client, api_user):
        """Test that remaining requests decreases"""
        responses = []
        for i in range(3):
            response = client.post(
                "/api/v1/todos",
                json={
                    "title": f"Test {i}",
                    "source_app": "TestApp",
                },
                headers={"Authorization": f"Bearer {api_user['key']}"},
            )
            responses.append(response)

        # Check that remaining count decreased
        remaining_1 = int(responses[0].headers.get("X-RateLimit-Remaining", 0))
        remaining_2 = int(responses[1].headers.get("X-RateLimit-Remaining", 0))
        remaining_3 = int(responses[2].headers.get("X-RateLimit-Remaining", 0))

        assert remaining_1 > remaining_2 > remaining_3


class TestApiKeyManagement:
    """Test API key generation and management"""

    def test_generate_api_key(self, client):
        """Test generating an API key"""
        with client.application.app_context():
            user = User.query.first()
            if not user:
                user = User(
                    google_id="test_keygen",
                    email="keygen@example.com",
                    name="KeyGen Test",
                )
                db.session.add(user)
                db.session.commit()

            # Generate key
            plain_key, api_key_obj = ApiKey.create_for_user(user.id)

            # Verify format
            assert plain_key.startswith("orb_")
            assert len(plain_key) == 36  # orb_ + 32 chars
            assert api_key_obj.key_prefix == plain_key[:12]

            # Verify it can be used
            verified = ApiKey.verify_key(plain_key)
            assert verified is not None
            assert verified.id == api_key_obj.id

    def test_one_key_per_user(self, client):
        """Test that only one key per user is allowed"""
        with client.application.app_context():
            user = User.query.filter_by(email="onekey_unique@example.com").first()
            if not user:
                user = User(
                    google_id="test_onekey",
                    email="onekey_unique@example.com",
                    name="OneKey Test",
                )
                db.session.add(user)
                db.session.commit()

            # Generate first key
            plain_key1, _ = ApiKey.create_for_user(user.id)

            # Generate second key (should replace first)
            plain_key2, _ = ApiKey.create_for_user(user.id)

            # Verify old key doesn't work
            old_verified = ApiKey.verify_key(plain_key1)
            assert old_verified is None

            # Verify new key works
            new_verified = ApiKey.verify_key(plain_key2)
            assert new_verified is not None

            # Verify only one key exists
            key_count = ApiKey.query.filter_by(user_id=user.id).count()
            assert key_count == 1
