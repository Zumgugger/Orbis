# Orbis Test Suite

This directory contains smoke tests for the Orbis application.

## Test Coverage

### Authentication Tests (`test_auth.py`)
- ✅ Login page loads/redirects
- ✅ Unauthenticated users redirected to login
- ✅ Logout functionality
- ✅ Authenticated access to protected pages
- ✅ Development mode login

### Todo Tests (`test_todos.py`)
- ✅ Todo list page loads
- ✅ Create new todos
- ✅ Toggle todo status (pending ↔ completed)
- ✅ Delete todos
- ⚠️ Edit todos (needs model field adjustments)
- ⚠️ User isolation (needs User import fix)

### Calendar Tests (`test_calendar.py`)
- ✅ Index page loads without calendar
- ✅ Tomorrow page loads
- ⚠️ Calendar API mocking (needs integration with actual calendar service)

### Ideas Tests (`test_ideas.py`)
- ✅ Ideas list page loads
- ✅ View idea details
- ⚠️ Create ideas (needs model field adjustments)
- ⚠️ Save notes/mindmap (404 errors - route investigation needed)
- ⚠️ File upload/download/delete (model schema issues)

## Running Tests

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_auth.py -v
```

### Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=term-missing
```

### Run in CI (GitHub Actions):
Tests run automatically on push/PR to `main` and `develop` branches.

## Test Infrastructure

### Fixtures (`conftest.py`)
- `app`: Test Flask application with temporary SQLite database
- `client`: Test client for making requests
- `test_user`: Creates a test user in the database
- `authenticated_client`: Client with logged-in session
- `sample_todo`: Sample todo for testing operations
- `sample_idea`: Sample idea for testing operations
- `mock_calendar_service`: Mock Google Calendar API

### Configuration
- Uses temporary SQLite database (created/destroyed per test session)
- CSRF protection disabled for easier testing
- Development mode enabled for dev login routes
- All database operations use transactions

## Dependencies

Test dependencies are in `requirements.txt`:
- `pytest>=7.4.0`
- `pytest-flask>=1.2.0`
- `pytest-cov>=4.1.0`
- `pytest-mock>=3.11.0`

## Known Issues

1. **Calendar Mocking**: Calendar API mocking needs integration with actual blueprints
2. **Ideas Routes**: Some ideas routes return 404 - need to verify route definitions
3. **Model Fields**: Some tests fail due to missing/renamed model fields
4. **SQLAlchemy Warnings**: Legacy Query.get() replaced with Session.get()

## Future Improvements

- [ ] Add integration tests for full user workflows
- [ ] Add tests for dailies, habits, goals, shopping features
- [ ] Improve calendar API mocking
- [ ] Add performance tests
- [ ] Add test data factories for easier fixture creation
- [ ] Set up test database seeding
- [ ] Add API endpoint tests if/when API is added
