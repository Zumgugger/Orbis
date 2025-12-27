# Orbis - Habit & Task Management System

A modular web application for managing habits, dailies, todos, and goals, inspired by Habitica.

## Features

### Current (v0.1)
- ✅ **Todo Management**: Create, edit, delete, and complete tasks
- ✅ Priority levels (low, medium, high)
- ✅ Due dates
- ✅ Clean, responsive UI with Bootstrap

### Planned
- 🔄 **Dailies**: Recurring daily tasks
- 🔄 **Habits**: Track positive/negative habits with counters
- 🔄 **Goals**: Long-term goals with progress tracking
- 🔄 **Google Calendar Integration**: Sync tasks and events
- 🔄 **Multi-user support**: Authentication and user accounts
- 🔄 **PostgreSQL**: Migration from SQLite for production
- 🔄 **Docker deployment**: Docker Compose setup for Ubuntu server

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite (development) → PostgreSQL (production)
- **Frontend**: Jinja2 templates, Bootstrap 5
- **Architecture**: Modular blueprints pattern

## Project Structure

```
Orbis/
├── app.py                 # Main application entry point
├── database.py            # Database models and initialization
├── requirements.txt       # Python dependencies
├── blueprints/            # Feature modules
│   └── todos.py          # Todo management routes
├── templates/             # HTML templates
│   ├── base.html         # Base layout
│   └── todos/            # Todo-specific templates
│       ├── list.html     # Todo list view
│       └── form.html     # Create/edit form
└── static/                # CSS, JS, images (future)
```

## Quick Start

### 1. Install Dependencies

```bash
cd Orbis
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the Application

```bash
python app.py
```

The application will be available at http://localhost:5000

### 3. Use the App

1. Navigate to http://localhost:5000
2. Click "New Todo" to create your first task
3. Fill in the title, description, priority, and due date
4. Click the circle icon to mark tasks as complete
5. Edit or delete tasks as needed

## Development Workflow

### Adding New Features

The app uses a modular blueprint structure to keep files small and focused:

1. Create a new blueprint in `blueprints/` (e.g., `dailies.py`, `habits.py`)
2. Add corresponding database models in `database.py`
3. Create templates in `templates/<feature>/`
4. Register the blueprint in `app.py`

### Database Changes (Alembic)

After modifying models in `database.py`:

```bash
# Create a new migration (auto-generates based on models)
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head
```

Existing runtime schema patching (`_ensure_*`) has been removed; use migrations to evolve the schema.

## Testing

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=term-missing
```

### Test Suite
Smoke tests cover core functionality:
- **Authentication**: Login/logout, dev mode, session management
- **Todos**: CRUD operations, status toggling, user isolation
- **Calendar**: Google Calendar integration (mocked)
- **Ideas**: Notes, mindmaps, file uploads

See [tests/README.md](tests/README.md) for detailed test documentation.

### Continuous Integration
Tests run automatically via GitHub Actions on push/PR to `main` and `develop` branches.

## Security Features

### File Upload Security
Comprehensive protection for idea file attachments:

- **10MB size limit** enforced before saving
- **Strict extension allowlist**: pdf, txt, md, odt, doc, docx, xls, xlsx, png, jpg, jpeg, gif, mp3, zip
- **MIME type validation** after upload (prevents renamed malware)
- **Random UUID subdirectories** (e.g., `ab/cd/uuid_filename.pdf`)
- **Path traversal protection** on all file operations
- **Secure filename sanitization** with werkzeug

See [FILE_UPLOAD_SECURITY.md](FILE_UPLOAD_SECURITY.md) for details.

Test security features:
```bash
python test_file_security.py
```

### Input Validation
Server-side validation for all form inputs via `validation.py`:
- Title/text length limits
- Date/time format validation
- Email validation
- Choice validation (priority, difficulty, frequency)
- Integer bounds checking

### Error Handling
- Custom 400/403/404/500 error pages
- JSON error responses for API endpoints
- Database rollback on errors
- Security error logging

## Future Deployment (Planned)

### PostgreSQL Migration
- Update `SQLALCHEMY_DATABASE_URI` in app configuration
- Use environment variables for connection strings

### Docker Deployment
- Create `Dockerfile` and `docker-compose.yml`
- Configure Apache reverse proxy on Ubuntu server
- Set up SSL/HTTPS certificates

## Contributing

This is a personal project, but feel free to fork and adapt for your own use!

## License

MIT
