"""
Pytest configuration and fixtures for Orbis tests
"""
import os
import tempfile
from datetime import date

import pytest

from app import create_app
from database import Daily, Goal, Habit, Idea, ShoppingList, Todo, User, db
from tests.factories import (
    DailyFactory,
    GoalFactory,
    HabitFactory,
    IdeaFactory,
    ShoppingListFactory,
    TodoFactory,
    UserFactory,
)


@pytest.fixture(scope="session")
def app():
    """Create and configure a test app instance"""
    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()

    # Set environment variables for testing
    os.environ["DEVELOPMENT_MODE"] = "true"
    os.environ["SECRET_KEY"] = "test-secret-key"

    test_app = create_app()
    test_app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "WTF_CSRF_ENABLED": False,  # Disable CSRF for testing
            "SECRET_KEY": "test-secret-key",
            "SERVER_NAME": "localhost.localdomain",  # Needed for URL generation in tests
        }
    )

    # Create database tables
    with test_app.app_context():
        db.create_all()

    yield test_app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Test client for making requests"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Test CLI runner"""
    return app.test_cli_runner()


@pytest.fixture(autouse=True)
def cleanup_database(app):
    """Clean up test data after each test"""
    yield
    # Clean up after test runs
    with app.app_context():
        # Get all test user IDs
        test_users = (
            db.session.query(User.id)
            .filter((User.email.like("%test%")) | (User.email.like("%other%")))
            .all()
        )
        test_user_ids = [user.id for user in test_users]

        if test_user_ids:
            # Delete all data belonging to test users (catches title changes)
            db.session.query(Todo).filter(Todo.user_id.in_(test_user_ids)).delete(
                synchronize_session=False
            )
            db.session.query(Idea).filter(Idea.user_id.in_(test_user_ids)).delete(
                synchronize_session=False
            )
            db.session.query(Daily).filter(Daily.user_id.in_(test_user_ids)).delete(
                synchronize_session=False
            )
            db.session.query(Habit).filter(Habit.user_id.in_(test_user_ids)).delete(
                synchronize_session=False
            )
            db.session.query(Goal).filter(Goal.user_id.in_(test_user_ids)).delete(
                synchronize_session=False
            )
            db.session.query(ShoppingList).filter(
                ShoppingList.user_id.in_(test_user_ids)
            ).delete(synchronize_session=False)

        # Clean up test users
        db.session.query(User).filter(
            (User.email.like("%test%")) | (User.email.like("%other%"))
        ).delete(synchronize_session=False)

        db.session.commit()


@pytest.fixture
def test_user(app):
    """Create a test user in the database using factory"""
    with app.app_context():
        # Clear any existing test users first
        db.session.query(User).filter(User.email == "test@example.com").delete()
        db.session.commit()

        user = UserFactory.create(
            google_id="test_google_123",
            email="test@example.com",
            name="Test User",
        )
        return user.id


@pytest.fixture
def admin_user(app):
    """Create an admin user for testing admin functionality"""
    with app.app_context():
        user = UserFactory.create_admin(
            email="admin@test.com",
            name="Admin User",
        )
        return user.id


@pytest.fixture
def authenticated_client(client, app, test_user):
    """Client with authenticated session"""
    # Use Flask-Login's test utilities to log in
    with app.test_request_context():
        with app.app_context():
            user = db.session.get(User, test_user)
            # Manually set up the session
            with client.session_transaction() as sess:
                sess["_user_id"] = str(test_user)
                sess["_fresh"] = True

    return client


@pytest.fixture
def sample_todo(app, test_user):
    """Create a sample todo for testing using factory"""
    with app.app_context():
        todo = TodoFactory.create(
            user_id=test_user,
            title="Test Todo",
            description="Test description",
            due_date=date.today(),
        )
        return todo.id


@pytest.fixture
def sample_idea(app, test_user):
    """Create a sample idea for testing using factory"""
    with app.app_context():
        idea = IdeaFactory.create(
            user_id=test_user,
            title="Test Idea",
            description="Test idea description",
            notes="Initial notes",
        )
        return idea.id


@pytest.fixture
def sample_daily(app, test_user):
    """Create a sample daily for testing"""
    with app.app_context():
        daily = DailyFactory.create(
            user_id=test_user,
            title="Test Daily",
        )
        return daily.id


@pytest.fixture
def sample_habit(app, test_user):
    """Create a sample habit for testing"""
    with app.app_context():
        habit = HabitFactory.create(
            user_id=test_user,
            title="Test Habit",
        )
        return habit.id


@pytest.fixture
def sample_goal(app, test_user):
    """Create a sample goal with milestones for testing"""
    with app.app_context():
        goal = GoalFactory.create_with_milestones(
            user_id=test_user,
            title="Test Goal",
            milestone_count=2,
        )
        return goal.id


@pytest.fixture
def sample_shopping_list(app, test_user):
    """Create a sample shopping list for testing"""
    with app.app_context():
        shopping_list = ShoppingListFactory.create(
            user_id=test_user,
            title="Test Shopping List",
        )
        return shopping_list.id


@pytest.fixture
def mock_calendar_service(monkeypatch):
    """Mock Google Calendar API service"""

    class MockCalendarService:
        def events(self):
            return self

        def list(self, calendarId, timeMin, timeMax, singleEvents, orderBy):
            return self

        def execute(self):
            return {
                "items": [
                    {
                        "id": "event1",
                        "summary": "Test Event",
                        "start": {"dateTime": "2025-12-27T10:00:00Z"},
                        "end": {"dateTime": "2025-12-27T11:00:00Z"},
                    }
                ]
            }

    def mock_build(*args, **kwargs):
        return MockCalendarService()

    # Mock the googleapiclient.discovery.build function
    monkeypatch.setattr("googleapiclient.discovery.build", mock_build)

    return MockCalendarService()
