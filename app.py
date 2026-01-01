"""
Orbis - Habit and Task Management System
Main application entry point
"""
import os
from datetime import timedelta

import bleach
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import current_user, login_required
from markdown import markdown as md_to_html
from markupsafe import Markup
from werkzeug.exceptions import HTTPException

from config import DevConfig, ProdConfig, TestConfig
from database import Daily, Habit, Todo, User, init_db
from exceptions import OrbisError
from extensions import csrf, db, login_manager
from services import CalendarService, RolloverService
from time_utils import today_local
from utilities import (
    combine_todos_and_calendar,
    error_message,
    error_response,
    filter_dailies_for_date,
)

# Load environment variables
load_dotenv()


def create_app(config_name=None):
    app = Flask(__name__)

    config_map = {
        "development": DevConfig,
        "production": ProdConfig,
        "test": TestConfig,
        "testing": TestConfig,
    }
    cfg_key = (
        config_name
        or os.getenv("ORBIS_CONFIG")
        or os.getenv("FLASK_ENV")
        or "development"
    ).lower()
    app_config = config_map.get(cfg_key, DevConfig)
    app.config.from_object(app_config)

    # Configure centralized logging
    from logging_config import configure_logging

    configure_logging(app)

    # Markdown filter for rendering section bodies (sanitized)
    allowed_tags = bleach.sanitizer.ALLOWED_TAGS.union(
        {"p", "pre", "code", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "hr"}
    )
    allowed_attrs = {"a": ["href", "title", "rel"], "img": ["src", "alt", "title"]}

    def render_markdown(text):
        raw_html = md_to_html(text or "", extensions=["extra"])
        safe_html = bleach.clean(
            raw_html, tags=allowed_tags, attributes=allowed_attrs, strip=True
        )
        return Markup(safe_html)

    app.jinja_env.filters["markdown"] = render_markdown
    # CSRF protection
    csrf.init_app(app)
    # Expose csrf_token to templates
    from flask_wtf.csrf import generate_csrf

    app.jinja_env.globals["csrf_token"] = generate_csrf

    # Security headers (only in production)
    if cfg_key == "production":
        from flask_talisman import Talisman

        # Content Security Policy - allow inline styles/scripts for app functionality
        csp = {
            "default-src": "'self'",
            "script-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
            "style-src": ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "https://cdn.jsdelivr.net"],
            "connect-src": "'self'",
        }
        Talisman(
            app,
            content_security_policy=csp,
            force_https=True,
            strict_transport_security=True,
            strict_transport_security_max_age=31536000,
            frame_options="DENY",
            content_security_policy_nonce_in=["script-src"],
        )

    # Initialize database
    init_db(app)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Initialize OAuth
    from blueprints.auth import init_oauth

    init_oauth(app)

    # Register blueprints
    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp
    from blueprints.dailies import dailies_bp
    from blueprints.goals import goals_bp
    from blueprints.habits import habits_bp
    from blueprints.ideas import ideas_bp
    from blueprints.masterprompts import masterprompts_bp
    from blueprints.notes import notes_bp
    from blueprints.search import search_bp
    from blueprints.shopping import shopping_bp
    from blueprints.tags import tags_bp
    from blueprints.todos import todos_bp

    # All blueprints now define url_prefix in their Blueprint() constructor
    app.register_blueprint(todos_bp)
    app.register_blueprint(dailies_bp)
    app.register_blueprint(habits_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(shopping_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(masterprompts_bp)
    app.register_blueprint(ideas_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(notes_bp)
    app.register_blueprint(tags_bp)

    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        return error_response(
            400, "bad_request", error_message(e, "Bad request"), "errors/400.html"
        )

    @app.errorhandler(403)
    def forbidden(e):
        return error_response(403, "forbidden", "Access denied", "errors/403.html")

    @app.errorhandler(404)
    def not_found(e):
        return error_response(
            404, "not_found", error_message(e, "Resource not found"), "errors/404.html"
        )

    @app.errorhandler(413)
    def request_entity_too_large(e):
        return error_response(
            413,
            "request_entity_too_large",
            "File too large. Maximum size is 10MB.",
            "errors/400.html",
        )

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()  # Rollback any failed transactions
        app.logger.error(f"Server Error: {e}")
        return error_response(
            500,
            "internal_server_error",
            "An unexpected error occurred",
            "errors/500.html",
        )

    @app.errorhandler(OrbisError)
    def handle_orbis_error(e: OrbisError):
        """Handle application-specific exceptions with proper response format."""
        db.session.rollback()
        template_map = {
            400: "errors/400.html",
            403: "errors/403.html",
            404: "errors/404.html",
        }
        template = template_map.get(e.status_code, "errors/500.html")
        if e.status_code >= 500:
            app.logger.error(f"Application error: {e.message}", extra=e.details)
        return error_response(e.status_code, e.error_code, e.message, template)

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all other exceptions."""
        db.session.rollback()
        if isinstance(e, HTTPException):
            template_map = {
                400: "errors/400.html",
                403: "errors/403.html",
                404: "errors/404.html",
                500: "errors/500.html",
            }
            template = template_map.get(getattr(e, "code", None), "errors/500.html")
            message = error_message(e, "An unexpected error occurred")
            error_key = (getattr(e, "name", None) or "error").lower().replace(" ", "_")
            return error_response(
                getattr(e, "code", 500) or 500, error_key, message, template
            )

        app.logger.exception(f"Unhandled exception: {e}")
        return error_response(
            500,
            "internal_server_error",
            "An unexpected error occurred",
            "errors/500.html",
        )

    # Initialize services
    calendar_service = CalendarService(app.logger)
    rollover_service = RolloverService(db.session)

    def fetch_calendar_events(user, start_date, end_date):
        """Fetch primary calendar events between start_date (inclusive) and end_date (exclusive)."""
        from blueprints.auth import get_google_token_for_user, oauth

        return calendar_service.fetch_events_for_user(
            user, start_date, end_date, get_google_token_for_user, oauth.google
        )

    def _update_todo_from_event(todo, event, today):
        """Update a todo's fields from a calendar event if changed."""
        # Update title if changed
        event_title = event.get("title", "Calendar Event")
        if todo.title != event_title:
            todo.title = event_title

        # Update description from calendar
        event_desc = event.get("description", "") or ""
        if todo.description != event_desc:
            todo.description = event_desc

        # Update times from calendar
        start_dt = event.get("start_dt")
        end_dt = event.get("end_dt")
        is_all_day = event.get("all_day", False)

        if start_dt and not is_all_day:
            new_due_date = start_dt.date()
            new_due_time = start_dt.time()
            if todo.due_date != new_due_date:
                todo.due_date = new_due_date
            if todo.due_time != new_due_time:
                todo.due_time = new_due_time

            if end_dt:
                new_end_time = end_dt.time()
                if todo.end_time != new_end_time:
                    todo.end_time = new_end_time
                # Recalculate duration
                new_duration = int((end_dt - start_dt).total_seconds() / 60)
                if todo.duration_minutes != new_duration:
                    todo.duration_minutes = new_duration
        elif start_dt and is_all_day:
            new_due_date = start_dt.date()
            if todo.due_date != new_due_date:
                todo.due_date = new_due_date
            todo.due_time = None
            todo.end_time = None

    def _parse_single_event(event_data):
        """Parse a single event from Google Calendar API response."""
        from datetime import datetime as dt

        start = event_data.get("start", {})
        end = event_data.get("end", {})

        # Check if all-day event
        all_day = "date" in start and "dateTime" not in start

        start_dt = None
        end_dt = None

        if all_day:
            start_str = start.get("date")
            end_str = end.get("date")
            if start_str:
                start_dt = dt.strptime(start_str, "%Y-%m-%d")
            if end_str:
                end_dt = dt.strptime(end_str, "%Y-%m-%d")
        else:
            start_str = start.get("dateTime")
            end_str = end.get("dateTime")
            if start_str:
                start_dt = dt.fromisoformat(start_str.replace("Z", "+00:00"))
            if end_str:
                end_dt = dt.fromisoformat(end_str.replace("Z", "+00:00"))

        return {
            "id": event_data.get("id"),
            "title": event_data.get("summary", ""),
            "description": event_data.get("description", ""),
            "start_dt": start_dt,
            "end_dt": end_dt,
            "all_day": all_day,
        }

    def _sync_calendar_events_to_todos(user):
        """Sync Google Calendar events to todos - create, update, and handle deletions."""
        from blueprints.auth import get_google_token_for_user, oauth

        today = today_local()

        try:
            token = get_google_token_for_user(user)
            if not token:
                return

            # Fetch events for today and tomorrow (for creating NEW todos)
            calendar_events = calendar_service.fetch_events_for_user(
                user,
                today,
                today + timedelta(days=2),
                get_google_token_for_user,
                oauth.google,
            )

            # Build a map of event_id -> event data
            events_by_id = {ev.get("id"): ev for ev in calendar_events if ev.get("id")}

            # Get existing todos linked to calendar events
            linked_todos = Todo.query.filter(
                Todo.user_id == user.id,
                Todo.google_event_id.isnot(None),
            ).all()

            existing_event_ids = set()
            for todo in linked_todos:
                existing_event_ids.add(todo.google_event_id)

                # Check if this event is in our 2-day fetch window
                if todo.google_event_id in events_by_id:
                    # Event exists in window - update from fetched data
                    event = events_by_id[todo.google_event_id]
                    _update_todo_from_event(todo, event, today)
                else:
                    # Event not in 2-day window - fetch it individually
                    event_data = calendar_service.get_event(
                        oauth.google, token, todo.google_event_id
                    )
                    if event_data:
                        # Event exists - parse and update todo
                        event = _parse_single_event(event_data)
                        _update_todo_from_event(todo, event, today)
                    else:
                        # Event was deleted from calendar - delete the todo
                        db.session.delete(todo)

            # Create todos for new events
            for event in calendar_events:
                event_id = event.get("id")
                if not event_id or event_id in existing_event_ids:
                    continue

                # Parse event times
                start_dt = event.get("start_dt")
                due_date = start_dt.date() if start_dt else today
                due_time = (
                    start_dt.time() if start_dt and not event.get("all_day") else None
                )

                end_dt = event.get("end_dt")
                end_time = (
                    end_dt.time() if end_dt and not event.get("all_day") else None
                )

                # Calculate duration
                duration_minutes = None
                if start_dt and end_dt and not event.get("all_day"):
                    duration_minutes = int((end_dt - start_dt).total_seconds() / 60)

                # Create the todo
                todo = Todo(
                    title=event.get("title", "Calendar Event"),
                    description=event.get("description", ""),
                    priority="medium",
                    due_date=due_date,
                    due_time=due_time,
                    end_time=end_time,
                    duration_minutes=duration_minutes,
                    user_id=user.id,
                    google_event_id=event_id,
                )
                db.session.add(todo)

            db.session.commit()
        except Exception as e:
            db.session.rollback()
            app.logger.warning(f"Failed to sync calendar events to todos: {e}")

    def process_rollover_for_user(user):
        """Shift unfinished items forward once per day and break missed streaks."""
        return rollover_service.process_rollover(user)

    @app.route("/")
    @login_required
    def index():
        rollover_result = process_rollover_for_user(current_user)
        missed_yesterday = rollover_result.get("missed_yesterday", [])
        # Sync calendar events to todos first
        _sync_calendar_events_to_todos(current_user)

        # Get todos due today for current user (all, including completed)
        today = today_local()
        target_date = today
        # Include todos with due_date=today OR todos with due_time but no due_date (implicit today)
        from sqlalchemy import and_, or_

        todos_today = Todo.query.filter(
            Todo.user_id == current_user.id,
            Todo.status.in_(["pending", "in_progress"]),
            or_(
                Todo.due_date == today,
                and_(Todo.due_date.is_(None), Todo.due_time.isnot(None)),
            ),
        ).all()

        # Get overdue todos (pending/in_progress with due_date before today)
        overdue_todos = (
            Todo.query.filter(
                Todo.user_id == current_user.id,
                Todo.status.in_(["pending", "in_progress"]),
                Todo.due_date < today,
            )
            .order_by(Todo.due_date.desc())
            .all()
        )

        # Get all dailies that should be done today OR were completed today (including completed ones)
        dailies_today = []
        all_dailies = Daily.query.filter_by(user_id=current_user.id).all()

        for daily in all_dailies:
            # Include if it should be done today OR if it was already completed today
            if daily.should_complete_today() or daily.is_completed_today():
                dailies_today.append(daily)

        # Get only the ones not yet completed for the "everything_done" check
        dailies_not_done = [d for d in dailies_today if not d.is_completed_today()]

        focused_habits = (
            Habit.query.filter_by(user_id=current_user.id, focused=True)
            .order_by(Habit.position.asc(), Habit.id.asc())
            .all()
        )
        focused_not_done = [h for h in focused_habits if h.last_increment_date != today]

        # Check if everything is done (no pending items)
        pending_todos = [t for t in todos_today if t.status == "pending"]
        everything_done = (
            len(pending_todos) == 0
            and len(dailies_not_done) == 0
            and len(focused_not_done) == 0
        )

        # Progress for Today
        total_today = len(dailies_today) + len(todos_today) + len(focused_habits)
        completed_today = (
            len([d for d in dailies_today if d.is_completed_today()])
            + len([t for t in todos_today if t.status == "completed"])
            + len([h for h in focused_habits if h.last_increment_date == today])
        )
        today_progress_percent = (
            int(round((completed_today / total_today) * 100)) if total_today > 0 else 0
        )

        # Fetch calendar events and combine with todos
        calendar_today = fetch_calendar_events(
            current_user, today, today + timedelta(days=1)
        )
        combined_todos = combine_todos_and_calendar(
            todos_today, calendar_today, "Today"
        )

        # Recalculate progress to match displayed items
        # Total: dailies + combined_todos (calendar + todos) + focused_habits
        total_today = len(dailies_today) + len(combined_todos) + len(focused_habits)
        # Completed: dailies completed + todos completed + habits incremented today
        completed_today = (
            len([d for d in dailies_today if d.is_completed_today()])
            + sum(
                1
                for item in combined_todos
                if item["kind"] == "todo" and item["todo"].status == "completed"
            )
            + len([h for h in focused_habits if h.last_increment_date == today])
        )
        today_progress_percent = (
            int(round((completed_today / total_today) * 100)) if total_today > 0 else 0
        )

        return render_template(
            "index.html",
            todos=todos_today,
            dailies=dailies_today,
            focused_habits=focused_habits,
            target_date=target_date,
            everything_done=everything_done,
            combined_todos=combined_todos,
            today_completed=completed_today,
            today_total=total_today,
            today_progress_percent=today_progress_percent,
            missed_yesterday=missed_yesterday,
            overdue_todos=overdue_todos,
        )

    @app.route("/tomorrow")
    @login_required
    def tomorrow():
        process_rollover_for_user(current_user)

        today = today_local()
        target_date = today + timedelta(days=1)

        todos_tomorrow = Todo.query.filter(
            Todo.user_id == current_user.id, Todo.due_date == target_date
        ).all()

        # Use utility function to filter dailies with carryover
        all_dailies = Daily.query.filter_by(user_id=current_user.id).all()
        dailies_tomorrow, carryover_ids = filter_dailies_for_date(
            all_dailies, target_date, include_carryover=True, carryover_date=today
        )

        focused_habits = (
            Habit.query.filter_by(user_id=current_user.id, focused=True)
            .order_by(Habit.position.asc(), Habit.id.asc())
            .all()
        )

        # Fetch calendar events and combine with todos
        calendar_tomorrow = fetch_calendar_events(
            current_user, target_date, target_date + timedelta(days=1)
        )
        combined_todos = combine_todos_and_calendar(
            todos_tomorrow, calendar_tomorrow, "Tomorrow"
        )

        # Progress for Tomorrow — count items shown in UI
        # Total: dailies + combined_todos (calendar + todos) + focused_habits
        total_tomorrow = (
            len(dailies_tomorrow) + len(combined_todos) + len(focused_habits)
        )
        # Completed: dailies completed + todos completed + habits incremented
        completed_tomorrow = (
            len([d for d in dailies_tomorrow if d.is_completed_on(target_date)])
            + sum(
                1
                for item in combined_todos
                if item["kind"] == "todo" and item["todo"].status == "completed"
            )
            + len([h for h in focused_habits if h.last_increment_date == target_date])
        )
        tomorrow_progress_percent = (
            int(round((completed_tomorrow / total_tomorrow) * 100))
            if total_tomorrow > 0
            else 0
        )

        return render_template(
            "tomorrow.html",
            todos=todos_tomorrow,
            dailies=dailies_tomorrow,
            carryover_ids=carryover_ids,
            focused_habits=focused_habits,
            target_date=target_date,
            combined_todos=combined_todos,
            tomorrow_completed=completed_tomorrow,
            tomorrow_total=total_tomorrow,
            tomorrow_progress_percent=tomorrow_progress_percent,
        )

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5001))
    app.run(debug=True, host="0.0.0.0", port=port)
