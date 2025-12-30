# Orbis Codebase Improvement Plan

A comprehensive 20-point plan to improve architecture, maintainability, and code cleanliness.

---

## 1. Extract Business Logic from Route Handlers into Service Layer

**Current State:** Business logic (rollover processing, streak calculations, calendar fetching) is embedded directly in `app.py` route handlers and model methods.

**Improvement:**
- Create a `services/` directory with dedicated service modules:
  - `services/rollover_service.py` - Handle todo rollover and streak reset
  - `services/calendar_service.py` - Google Calendar integration
  - `services/completion_service.py` - Daily/Todo completion tracking
- Routes become thin controllers that delegate to services

**Benefits:** Better testability, single responsibility, easier to modify business rules independently.

---

## 2. Consolidate Database Models into Separate Module Files

**Current State:** `database.py` is 824 lines containing all models, making it hard to navigate.

**Improvement:**
- Create `models/` directory with separate files:
  - `models/user.py` - User, RolloverState
  - `models/todo.py` - Todo model
  - `models/daily.py` - Daily, CompletionLog
  - `models/habit.py` - Habit model
  - `models/goal.py` - Goal, Milestone
  - `models/shopping.py` - ShoppingList
  - `models/idea.py` - Idea, IdeaFile
  - `models/masterprompt.py` - MasterCategory, MasterSection
  - `models/__init__.py` - Re-export all models
- Keep `database.py` for `init_db()` and migration utilities only

**Benefits:** Easier navigation, focused files, better code organization.

---

## 3. Replace Inline Migrations with Proper Alembic Usage

**Current State:** `apply_migrations()` in `database.py` runs raw SQL at startup to add columns, bypassing Alembic.

**Improvement:**
- Remove inline `apply_migrations()` function
- Create proper Alembic migrations for all schema changes
- Use `flask db migrate` / `flask db upgrade` workflow
- Add pre-deployment migration checks to CI/CD

**Benefits:** Proper schema versioning, safer production deployments, team collaboration on schema changes.

---

## 4. Standardize Blueprint Structure with Consistent Patterns

**Current State:** Blueprints have inconsistent naming (e.g., `goals.list` vs `todos.list_todos`, `goals.edit` vs `todos.edit_todo`).

**Improvement:**
- Adopt consistent route naming convention across all blueprints:
  - `<resource>.list` - List all items
  - `<resource>.create` - Create new item
  - `<resource>.view` - View single item
  - `<resource>.edit` - Edit item
  - `<resource>.delete` - Delete item
- Create a base blueprint class or factory for common CRUD patterns

**Benefits:** Predictable API surface, easier URL generation, reduced cognitive load.

---

## 5. Implement Repository Pattern for Database Access

**Current State:** Direct `db.session` and `Model.query` calls scattered throughout blueprints.

**Improvement:**
- Create `repositories/` directory with data access classes:
  - `repositories/todo_repository.py`
  - `repositories/daily_repository.py`
  - etc.
- Encapsulate all database queries (filtering, ordering, pagination)
- Blueprints inject repositories via dependency injection

**Benefits:** Centralized query logic, easier testing with mocks, swappable data sources.

---

## 6. Add Type Hints Throughout Codebase

**Current State:** Minimal type annotations despite having `mypy.ini` configured.

**Improvement:**
- Add type hints to all function signatures
- Define typed dataclasses or TypedDicts for complex return types
- Enable strict mypy checking gradually
- Add `py.typed` marker for type-aware imports

**Benefits:** Better IDE support, catch bugs early, self-documenting code.

---

## 7. Extract Repeated Form Handling into Flask-WTF Forms

**Current State:** Manual `request.form.get()` with validation in every route.

**Improvement:**
- Create `forms/` directory with WTForms classes:
  - `forms/todo_forms.py` - TodoCreateForm, TodoEditForm
  - `forms/daily_forms.py` - DailyForm
  - etc.
- Use form validation instead of manual `validate_*` calls
- Leverage CSRF protection built into Flask-WTF

**Benefits:** DRY validation, automatic CSRF, reusable form rendering.

---

## 8. Implement Proper Error Handling Strategy

**Current State:** Mixed error handling - some routes return JSON errors, others use flash messages, exception handlers in `app.py`.

**Improvement:**
- Create `exceptions.py` with domain-specific exceptions:
  - `NotFoundError`, `ForbiddenError`, `ValidationError`
- Implement consistent API error response format
- Add request content-type detection for JSON vs HTML responses
- Create error handler decorators for blueprints

**Benefits:** Consistent error responses, better API experience, easier debugging.

---

## 9. Add Request/Response DTOs (Data Transfer Objects)

**Current State:** Raw dicts and model `to_dict()` methods for serialization.

**Improvement:**
- Create `schemas/` directory with Pydantic or Marshmallow schemas:
  - `schemas/todo_schema.py`
  - `schemas/daily_schema.py`
- Use schemas for request validation and response serialization
- Add API versioning consideration

**Benefits:** Validated inputs, consistent outputs, documentation-ready schemas.

---

## 10. Refactor Daily Model's Complex Business Logic

**Current State:** `Daily` model has 150+ lines of complex streak/frequency logic in `toggle_completion()` and `toggle_completion_on()`.

**Improvement:**
- Extract frequency calculation into `FrequencyCalculator` class
- Extract streak tracking into `StreakTracker` class
- Use strategy pattern for different frequency types
- Add comprehensive unit tests for edge cases

**Benefits:** Testable logic, single responsibility, easier to add new frequency types.

---

## 11. Centralize Configuration with Environment Validation

**Current State:** `config.py` uses `os.getenv()` with fallbacks, no validation of required settings.

**Improvement:**
- Use `pydantic-settings` or similar for typed configuration
- Validate required environment variables at startup
- Add configuration schema documentation
- Separate secrets from non-sensitive config

**Benefits:** Fail-fast on missing config, type-safe access, documented settings.

---

## 12. Add Logging Consistency and Structure

**Current State:** Inconsistent logging - some uses `app.logger`, some uses `log_warning()` from utilities.

**Improvement:**
- Create `logging_config.py` with structured logging setup
- Use structured logging (JSON format) for production
- Add correlation IDs for request tracing
- Standardize log levels across modules
- Remove duplicate logging utilities

**Benefits:** Better observability, easier debugging, production-ready logging.

---

## 13. Implement API Rate Limiting and Security Headers

**Current State:** No rate limiting, minimal security headers.

**Improvement:**
- Add Flask-Limiter for rate limiting
- Implement security headers via Flask-Talisman:
  - CSP, X-Frame-Options, X-Content-Type-Options
- Add request size limits
- Implement API key authentication for external access

**Benefits:** DDoS protection, XSS mitigation, production security.

---

## 14. Refactor Template Organization and Partials

**Current State:** Templates have some duplication, limited partial usage.

**Improvement:**
- Create `templates/partials/` for reusable components:
  - `_pagination.html`, `_flash_messages.html`, `_form_errors.html`
- Add template inheritance hierarchy review
- Create component macros for common UI patterns
- Add template linting with djLint

**Benefits:** DRY templates, consistent UI, faster frontend development.

---

## 15. Add Database Query Optimization

**Current State:** N+1 queries possible (e.g., loading ideas with files), some indexes exist.

**Improvement:**
- Add SQLAlchemy query profiling in development
- Use `selectinload()` consistently for relationships
- Review and add missing database indexes
- Add query result caching with Flask-Caching for expensive operations
- Implement pagination for list endpoints

**Benefits:** Better performance, reduced database load, scalability.

---

## 16. Improve Test Coverage and Structure

**Current State:** Tests exist but `conftest.py` has complex cleanup logic, limited fixture reuse.

**Improvement:**
- Use factory_boy for test data generation
- Create `tests/factories/` with model factories
- Add integration tests for critical flows
- Implement test database transactions with automatic rollback
- Add coverage reporting and minimum threshold

**Benefits:** Reliable tests, faster test development, better coverage.

---

## 17. Add API Documentation

**Current State:** No API documentation, routes serve both HTML and JSON.

**Improvement:**
- Add OpenAPI/Swagger documentation with Flask-RESTX or flasgger
- Document all JSON endpoints
- Add request/response examples
- Generate interactive API explorer

**Benefits:** Self-documenting API, easier integration, developer onboarding.

---

## 18. Implement Background Task Processing

**Current State:** Rollover processing happens synchronously on request, calendar fetching blocks responses.

**Improvement:**
- Add Celery or RQ for background tasks
- Move rollover processing to scheduled tasks
- Make calendar sync asynchronous
- Add task monitoring and retry logic

**Benefits:** Faster responses, reliable background processing, scalable architecture.

---

## 19. Add Feature Flags and Configuration Toggle

**Current State:** No feature flag system, all features always enabled.

**Improvement:**
- Implement simple feature flag system
- Support user-level and global toggles
- Add A/B testing capability
- Enable gradual rollouts

**Benefits:** Safe deployments, controlled rollouts, experimentation capability.

---

## 20. Create Development and Operations Documentation

**Current State:** Basic README, limited setup documentation.

**Improvement:**
- Expand README with architecture overview
- Add `docs/` directory with:
  - `docs/ARCHITECTURE.md` - System design
  - `docs/DEVELOPMENT.md` - Setup and workflow
  - `docs/DEPLOYMENT.md` - Production deployment
  - `docs/API.md` - API reference (or link to generated docs)
- Add ADR (Architecture Decision Records) for major decisions
- Create runbook for common operations

**Benefits:** Easier onboarding, knowledge preservation, operational clarity.

---

## Priority Order

### High Priority (Address First)
1. **#2** - Split database models (foundation for other changes)
2. **#6** - Add type hints (improves all subsequent work)
3. **#3** - Fix migrations (production safety)
4. **#8** - Standardize error handling (user experience)

### Medium Priority (Next Phase)
5. **#1** - Service layer extraction
6. **#4** - Blueprint standardization
7. **#10** - Daily model refactor
8. **#15** - Query optimization
9. **#16** - Test improvements

### Lower Priority (Future Improvements)
10. **#5** - Repository pattern
11. **#7** - WTForms migration
12. **#9** - DTOs/Schemas
13. **#11** - Config validation
14. **#12** - Logging improvements
15. **#13** - Security hardening
16. **#14** - Template refactoring
17. **#17** - API documentation
18. **#18** - Background tasks
19. **#19** - Feature flags
20. **#20** - Documentation

---

## Estimated Effort

| Improvement | Effort | Risk |
|-------------|--------|------|
| #1 Service Layer | High | Medium |
| #2 Split Models | Medium | Low |
| #3 Fix Migrations | Low | Medium |
| #4 Blueprint Standard | Medium | Low |
| #5 Repository Pattern | High | Low |
| #6 Type Hints | Medium | Low |
| #7 WTForms | Medium | Medium |
| #8 Error Handling | Low | Low |
| #9 DTOs | Medium | Low |
| #10 Daily Refactor | High | Medium |
| #11 Config | Low | Low |
| #12 Logging | Low | Low |
| #13 Security | Low | Low |
| #14 Templates | Medium | Low |
| #15 Query Optimization | Medium | Low |
| #16 Tests | Medium | Low |
| #17 API Docs | Low | Low |
| #18 Background Tasks | High | Medium |
| #19 Feature Flags | Low | Low |
| #20 Documentation | Low | Low |

---

*Generated: December 30, 2025*
