"""
Orbis - Habit and Task Management System
Main application entry point
"""
import os
from datetime import date, datetime, timedelta

import bleach
from dotenv import load_dotenv
from flask import Flask, render_template
from flask_login import current_user, login_required
from markdown import markdown as md_to_html
from markupsafe import Markup
from werkzeug.exceptions import HTTPException

from config import DevConfig, ProdConfig, TestConfig
from database import Daily, Habit, RolloverState, Todo, User, init_db
from extensions import csrf, db, login_manager
from time_utils import get_local_tz, iso_start_of_day, today_local
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

    # Initialize database
    init_db(app)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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
    from blueprints.search import search_bp
    from blueprints.shopping import shopping_bp
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

    @app.errorhandler(Exception)
    def handle_exception(e):
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

    def fetch_calendar_events(user, start_date, end_date):
        """Fetch primary calendar events between start_date (inclusive) and end_date (exclusive)."""
        from blueprints.auth import get_google_token_for_user, oauth

        token = get_google_token_for_user(user, logger=app.logger)
        if not token:
            return []

        tz = get_local_tz()

        time_min = iso_start_of_day(start_date)
        time_max = iso_start_of_day(end_date)

        try:
            resp = oauth.google.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "timeMin": time_min,
                    "timeMax": time_max,
                    "singleEvents": True,
                    "orderBy": "startTime",
                },
                token=token,
            )
        except Exception as exc:
            app.logger.warning(f"Calendar fetch failed: {exc}")
            return []

        if resp.status_code != 200:
            app.logger.warning(
                f"Calendar fetch returned {resp.status_code}: {resp.text}"
            )
            return []

        events = []
        data = resp.json()
        for item in data.get("items", []):
            start = item.get("start", {})
            end = item.get("end", {})
            is_all_day = "date" in start
            raw_start = start.get("dateTime") or start.get("date")
            raw_end = end.get("dateTime") or end.get("date")

            def fmt_dt(val):
                if not val:
                    return None
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    if tz:
                        dt = dt.astimezone(tz)
                    return dt
                except Exception:
                    return None

            start_dt = fmt_dt(raw_start) if not is_all_day else None
            end_dt = fmt_dt(raw_end) if not is_all_day else None
            events.append(
                {
                    "title": item.get("summary") or "(No title)",
                    "start_raw": raw_start,
                    "end_raw": raw_end,
                    "start_dt": start_dt,
                    "end_dt": end_dt,
                    "all_day": is_all_day,
                    "html_link": item.get("htmlLink"),
                }
            )

        return events

    def process_rollover_for_user(user):
        """Shift unfinished items forward once per day and break missed streaks."""
        if not user.is_authenticated:
            return

        today = date.today()
        state = RolloverState.query.filter_by(user_id=user.id).first()

        if not state:
            state = RolloverState(user_id=user.id, last_processed_date=today)
            db.session.add(state)
            db.session.commit()
            return

        current_day = state.last_processed_date

        while current_day < today:
            next_day = current_day + timedelta(days=1)

            # Move pending todos forward by one day
            pending_todos = Todo.query.filter(
                Todo.user_id == user.id,
                Todo.status == "pending",
                Todo.due_date == current_day,
            ).all()
            for todo in pending_todos:
                todo.due_date = next_day

            # Break streak for dailies missed on the day
            user_dailies = Daily.query.filter_by(user_id=user.id).all()
            for daily in user_dailies:
                if daily.should_complete_on(current_day) and not daily.is_completed_on(
                    current_day
                ):
                    daily.streak_count = 0

            db.session.commit()
            current_day = next_day

        state.last_processed_date = today
        db.session.commit()

    @app.route("/")
    @login_required
    def index():
        process_rollover_for_user(current_user)
        # Get todos due today for current user (all, including completed)
        today = today_local()
        target_date = today
        todos_today = Todo.query.filter(
            Todo.user_id == current_user.id, Todo.due_date == today
        ).all()

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

        # Progress for Tomorrow
        total_tomorrow = len(dailies_tomorrow) + len(todos_tomorrow)
        completed_tomorrow = len(
            [d for d in dailies_tomorrow if d.is_completed_on(target_date)]
        ) + len([t for t in todos_tomorrow if t.status == "completed"])
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
