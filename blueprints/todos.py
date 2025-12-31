"""
Todos Blueprint - handles all todo/task related routes
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Todo
from time_utils import get_local_tz, now_local, today_local, tomorrow_local
from utilities import log_error, log_exception, log_warning
from validation import (
    ValidationError,
    validate_date,
    validate_duration,
    validate_integer,
    validate_priority,
    validate_text,
    validate_time,
    validate_title,
)

todos_bp = Blueprint("todos", __name__, url_prefix="/todos")


def _parse_time_fields(form: dict) -> dict:
    """Parse time scheduling fields from form data."""
    due_time = validate_time(form.get("due_time"))
    end_time = validate_time(form.get("end_time"))
    duration_minutes = validate_integer(
        form.get("duration_minutes"),
        field_name="Duration",
        min_val=1,
        max_val=1440,  # max 24 hours
    )

    # If end_time provided, calculate duration automatically
    if due_time and end_time and not duration_minutes:
        from datetime import datetime

        start_dt = datetime.combine(datetime.today(), due_time)
        end_dt = datetime.combine(datetime.today(), end_time)
        if end_dt > start_dt:
            duration_minutes = int((end_dt - start_dt).total_seconds() // 60)

    return {
        "due_time": due_time,
        "end_time": end_time,
        "duration_minutes": duration_minutes,
    }


@todos_bp.route("/quick_create", methods=["POST"])
@login_required
def quick_create():
    """Quick create todo from selected text (AJAX endpoint)"""
    try:
        data = request.get_json() or {}
        title = validate_title(data.get("title"), max_length=200)

        todo = Todo(
            title=title,
            description=data.get("description", ""),
            priority="medium",
            due_date=None,
            user_id=current_user.id,
        )
        db.session.add(todo)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Todo created",
                "todo": {
                    "id": todo.id,
                    "title": todo.title,
                    "url": url_for("todos.edit_todo", todo_id=todo.id),
                },
            }
        )
    except ValidationError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"success": False, "error": "Failed to create todo"}), 500


@todos_bp.route("/")
@login_required
def list_todos():
    """Display all todos, syncing calendar events to todos"""
    # Sync calendar events to todos first
    _sync_calendar_events_to_todos()

    # Then get all todos
    todos = (
        Todo.query.filter_by(user_id=current_user.id)
        .order_by(Todo.position.asc(), Todo.created_at.desc())
        .all()
    )
    pending = [t for t in todos if t.status in ("pending", "in_progress")]
    completed = [t for t in todos if t.status == "completed"]

    return render_template(
        "todos/list.html",
        pending=pending,
        completed=completed,
    )


@todos_bp.route("/reorder", methods=["POST"])
@login_required
def reorder_todos():
    """Persist drag-and-drop order of pending todos for the current user"""
    payload = request.get_json(silent=True) or {}
    order = payload.get("order", [])
    if not isinstance(order, list):
        return {"success": False, "error": "Invalid order payload"}, 400

    try:
        for position, todo_id in enumerate(order):
            todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first()
            if todo and todo.status in ("pending", "in_progress"):
                todo.position = position
        db.session.commit()
        return {"success": True}, 200
    except Exception:
        db.session.rollback()
        return {"success": False, "error": "Failed to persist order"}, 500


@todos_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_todo():
    """Create a new todo"""
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            description = validate_text(
                request.form.get("description"), max_length=5000
            )
            priority = validate_priority(request.form.get("priority"))
            due_date = validate_date(request.form.get("due_date"))
            time_fields = _parse_time_fields(request.form)

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                due_time=time_fields["due_time"],
                end_time=time_fields["end_time"],
                duration_minutes=time_fields["duration_minutes"],
                user_id=current_user.id,
            )
            db.session.add(todo)
            db.session.commit()

            flash("Todo created successfully!", "success")
            return redirect(url_for("todos.list_todos"))
        except ValidationError as e:
            flash(str(e), "error")
            log_warning("Validation error creating todo", extra={"error": str(e)})
            return redirect(url_for("todos.create_todo"))

    return render_template(
        "todos/form.html",
        todo=None,
        action="Create",
        show_due_date=True,
        preset_due_date="",
    )


@todos_bp.route("/create/today", methods=["GET", "POST"])
@login_required
def create_todo_today():
    """Create a new todo due today without showing date picker"""
    preset_date = today_local()
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            description = validate_text(
                request.form.get("description"), max_length=5000
            )
            priority = validate_priority(request.form.get("priority"))
            time_fields = _parse_time_fields(request.form)

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=preset_date,
                due_time=time_fields["due_time"],
                end_time=time_fields["end_time"],
                duration_minutes=time_fields["duration_minutes"],
                user_id=current_user.id,
            )
            db.session.add(todo)
            db.session.commit()

            flash("Todo for today created!", "success")
            return redirect(url_for("index"))
        except ValidationError as e:
            flash(str(e), "error")
            log_warning("Validation error creating today todo", extra={"error": str(e)})
            return redirect(url_for("todos.create_todo_today"))

    return render_template(
        "todos/form.html",
        todo=None,
        action="Create",
        show_due_date=False,
        preset_due_date=preset_date.isoformat(),
    )


@todos_bp.route("/create/tomorrow", methods=["GET", "POST"])
@login_required
def create_todo_tomorrow():
    """Create a new todo due tomorrow without showing date picker"""
    preset_date = tomorrow_local()
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            description = validate_text(
                request.form.get("description"), max_length=5000
            )
            priority = validate_priority(request.form.get("priority"))
            time_fields = _parse_time_fields(request.form)

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=preset_date,
                due_time=time_fields["due_time"],
                end_time=time_fields["end_time"],
                duration_minutes=time_fields["duration_minutes"],
                user_id=current_user.id,
            )
            db.session.add(todo)
            db.session.commit()

            flash("Todo for tomorrow created!", "success")
            return redirect(url_for("tomorrow"))
        except ValidationError as e:
            flash(str(e), "error")
            log_warning(
                "Validation error creating tomorrow todo", extra={"error": str(e)}
            )
            return redirect(url_for("todos.create_todo_tomorrow"))

    return render_template(
        "todos/form.html",
        todo=None,
        action="Create",
        show_due_date=False,
        preset_due_date=preset_date.isoformat(),
    )


@todos_bp.route("/<int:todo_id>/edit", methods=["GET", "POST"])
@login_required
def edit_todo(todo_id):
    """Edit an existing todo"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        try:
            todo.title = validate_title(request.form.get("title"), max_length=200)
            todo.description = validate_text(
                request.form.get("description"), max_length=5000
            )
            todo.priority = validate_priority(request.form.get("priority"))
            todo.due_date = validate_date(request.form.get("due_date"))

            time_fields = _parse_time_fields(request.form)
            todo.due_time = time_fields["due_time"]
            todo.end_time = time_fields["end_time"]
            todo.duration_minutes = time_fields["duration_minutes"]

            # Mark as in progress when edited (per tests expectation)
            if todo.status == "pending":
                todo.status = "in_progress"
            db.session.commit()

            # Sync with Google Calendar if linked
            if todo.google_event_id:
                _sync_todo_to_calendar(todo)

            flash("Todo updated successfully!", "success")
            return redirect(url_for("todos.list_todos"))
        except ValidationError as e:
            flash(str(e), "error")
            log_warning(
                "Validation error editing todo",
                extra={"todo_id": todo_id, "error": str(e)},
            )
            return render_template("todos/form.html", todo=todo, action="Edit")

    return render_template("todos/form.html", todo=todo, action="Edit")


@todos_bp.route("/<int:todo_id>/toggle", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    """Toggle todo completion status and sync with Google Calendar if linked"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    if todo.status == "pending":
        todo.status = "completed"
        todo.completed_at = datetime.utcnow()

        # Sync completion to Google Calendar if linked
        if todo.google_event_id:
            _sync_calendar_completion(todo, mark_completed=True)
    else:
        todo.status = "pending"
        todo.completed_at = None

        # Remove completion mark from calendar if linked
        if todo.google_event_id:
            _sync_calendar_completion(todo, mark_completed=False)

    db.session.commit()
    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
    return redirect(url_for("todos.list_todos"))


def _sync_calendar_events_to_todos() -> None:
    """Sync Google Calendar events to todos - create todos for new events."""
    from time_utils import today_local

    today = today_local()

    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService

        token = get_google_token_for_user(current_user)
        if not token:
            return

        calendar_service = CalendarService(current_app.logger)
        # Fetch events for today and tomorrow to catch upcoming items
        calendar_events = calendar_service.fetch_events_for_user(
            current_user,
            today,
            today + timedelta(days=2),
            get_google_token_for_user,
            oauth.google,
        )

        # Get existing todos linked to calendar events
        existing_event_ids = {
            t.google_event_id
            for t in Todo.query.filter(
                Todo.user_id == current_user.id,
                Todo.google_event_id.isnot(None),
            ).all()
        }

        # Create todos for events that don't have one yet
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
            end_time = end_dt.time() if end_dt and not event.get("all_day") else None

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
                user_id=current_user.id,
                google_event_id=event_id,
            )
            db.session.add(todo)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        log_warning(f"Failed to sync calendar events to todos: {e}")


def _sync_calendar_completion(todo: Todo, mark_completed: bool) -> None:
    """Sync todo completion status to linked Google Calendar event."""
    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService

        token = get_google_token_for_user(current_user)
        if not token:
            return

        calendar_service = CalendarService(current_app.logger)

        if mark_completed:
            calendar_service.update_event(
                oauth.google,
                token,
                todo.google_event_id,
                mark_completed=True,
            )
        else:
            calendar_service.unmark_completed(
                oauth.google,
                token,
                todo.google_event_id,
            )
    except Exception as e:
        log_warning(
            f"Failed to sync calendar completion: {e}",
            extra={"todo_id": todo.id, "event_id": todo.google_event_id},
        )


def _sync_todo_to_calendar(todo: Todo) -> None:
    """Sync todo time and description changes to linked Google Calendar event."""
    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService

        token = get_google_token_for_user(current_user)
        if not token:
            return

        calendar_service = CalendarService(current_app.logger)

        # Build event times from todo fields
        start_time = None
        end_time = None
        event_date = todo.due_date

        if todo.due_time:
            tzinfo = get_local_tz()
            event_date = todo.due_date or date.today()
            start_time = datetime.combine(event_date, todo.due_time, tzinfo=tzinfo)
            duration = todo.duration_minutes or 60
            if todo.end_time:
                end_time = datetime.combine(event_date, todo.end_time, tzinfo=tzinfo)
            else:
                end_time = start_time + timedelta(minutes=duration)

        # Update the calendar event
        calendar_service.update_event(
            oauth.google,
            token,
            todo.google_event_id,
            title=todo.title,
            description=todo.description,
            start_time=start_time,
            end_time=end_time,
            event_date=event_date if not start_time else None,
        )
    except Exception as e:
        log_warning(
            f"Failed to sync todo to calendar: {e}",
            extra={"todo_id": todo.id, "event_id": todo.google_event_id},
        )


@todos_bp.route("/<int:todo_id>/delete", methods=["POST"])
@login_required
def delete_todo(todo_id):
    """Delete a todo"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    db.session.delete(todo)
    db.session.commit()
    flash("Todo deleted successfully!", "success")
    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/due/today", methods=["POST"])
@login_required
def set_due_today(todo_id):
    """Set todo due date to today"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    todo.due_date = date.today()
    db.session.commit()
    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/due/tomorrow", methods=["POST"])
@login_required
def set_due_tomorrow(todo_id):
    """Set todo due date to tomorrow"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    todo.due_date = date.today() + timedelta(days=1)
    db.session.commit()
    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/schedule", methods=["POST"])
@login_required
def schedule_todo(todo_id):
    """Schedule a todo as a Google Calendar event (creates bidirectional link)"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    # Check if already linked to a calendar event
    if todo.google_event_id:
        flash("This todo is already linked to a calendar event.", "warning")
        return redirect(url_for("todos.list_todos"))

    try:
        event_date = validate_date(request.form.get("event_date"), required=True)
        event_time = validate_time(request.form.get("event_time"))
        duration_hours, duration_minutes = validate_duration(
            request.form.get("duration_hours"), request.form.get("duration_minutes")
        )
    except ValidationError as e:
        flash(str(e), "error")
        log_warning(
            "Validation error scheduling todo",
            extra={"todo_id": todo.id, "error": str(e)},
        )
        return redirect(url_for("todos.list_todos"))

    # Warn if scheduling in the past
    if event_date < today_local():
        flash("Warning: You are scheduling an event in the past.", "warning")
        log_warning(
            "Scheduling event in the past",
            extra={"todo_id": todo.id, "event_date": event_date.isoformat()},
        )
    elif event_date == today_local() and event_time:
        now = now_local()
        tzinfo = get_local_tz()
        if datetime.combine(event_date, event_time, tzinfo=tzinfo) < now:
            flash("Warning: You are scheduling an event in the past.", "warning")
            log_warning(
                "Scheduling event in the past (same day)", extra={"todo_id": todo.id}
            )

    # Build event start/end time
    if event_time:
        tzinfo = get_local_tz()
        start_dt = datetime.combine(event_date, event_time, tzinfo=tzinfo)
        total_minutes = (duration_hours * 60) + duration_minutes
        end_dt = start_dt + timedelta(minutes=total_minutes)
    else:
        # All-day event
        start_dt = None
        end_dt = None

    # Call Google Calendar API via CalendarService
    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService

        token = get_google_token_for_user(current_user)
        if not token:
            flash("You must authenticate with Google first.", "error")
            log_warning("Missing Google auth token", extra={"todo_id": todo.id})
            return redirect(url_for("auth.login"))

        title = (str(todo.title).strip() if todo.title else "").strip()
        if not title:
            title = f"Todo #{todo.id}"

        calendar_service = CalendarService(current_app.logger)
        result = calendar_service.create_event(
            oauth_client=oauth.google,
            token=token,
            title=title,
            description=todo.description,
            event_date=event_date if not start_dt else None,
            start_time=start_dt,
            end_time=end_dt,
            duration_minutes=(duration_hours * 60) + duration_minutes,
        )

        if result:
            # Store the calendar event ID for bidirectional sync
            todo.google_event_id = result.get("id")
            # Also update todo's time fields to match scheduled time
            if event_time:
                todo.due_date = event_date
                todo.due_time = event_time
                if end_dt:
                    todo.end_time = end_dt.time()
                todo.duration_minutes = (duration_hours * 60) + duration_minutes
            db.session.commit()
            flash("Todo scheduled in Google Calendar!", "success")
        else:
            flash("Failed to create calendar event.", "error")
            log_error(
                "CalendarService.create_event returned None",
                extra={"todo_id": todo.id},
            )
    except Exception as e:
        flash(f"Error scheduling event: {str(e)}", "error")
        log_exception(
            e, message="Exception scheduling calendar event", extra={"todo_id": todo.id}
        )

    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/unlink_calendar", methods=["POST"])
@login_required
def unlink_calendar(todo_id):
    """Unlink a todo from its Google Calendar event (optionally delete the event)"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    if not todo.google_event_id:
        flash("This todo is not linked to a calendar event.", "warning")
        return redirect(url_for("todos.list_todos"))

    delete_event = request.form.get("delete_event") == "true"

    if delete_event:
        try:
            from flask import current_app

            from blueprints.auth import get_google_token_for_user, oauth
            from services import CalendarService

            token = get_google_token_for_user(current_user)
            if token:
                calendar_service = CalendarService(current_app.logger)
                calendar_service.delete_event(
                    oauth.google,
                    token,
                    todo.google_event_id,
                )
        except Exception as e:
            log_warning(
                f"Failed to delete calendar event: {e}",
                extra={"todo_id": todo.id, "event_id": todo.google_event_id},
            )

    # Clear the link regardless
    todo.google_event_id = None
    db.session.commit()
    flash("Todo unlinked from calendar event.", "success")

    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/quick_schedule", methods=["POST"])
@login_required
def quick_schedule(todo_id):
    """Quickly add todo to Google Calendar using existing time fields (no form needed)"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    # Check if already linked
    if todo.google_event_id:
        flash("This todo is already linked to a calendar event.", "warning")
        return redirect(url_for("todos.list_todos"))

    # Must have at least a due_date or due_time
    if not todo.due_date and not todo.due_time:
        flash("Please set a due date or time first.", "warning")
        return redirect(url_for("todos.list_todos"))

    # Default to today if no due_date but has time
    event_date = todo.due_date or date.today()

    # Build event times from todo fields
    if todo.due_time:
        tzinfo = get_local_tz()
        start_dt = datetime.combine(event_date, todo.due_time, tzinfo=tzinfo)
        duration = todo.duration_minutes or 60  # Default 1 hour
        if todo.end_time:
            end_dt = datetime.combine(event_date, todo.end_time, tzinfo=tzinfo)
        else:
            end_dt = start_dt + timedelta(minutes=duration)
    else:
        # All-day event
        start_dt = None
        end_dt = None

    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService

        token = get_google_token_for_user(current_user)
        if not token:
            flash("You must authenticate with Google first.", "error")
            return redirect(url_for("auth.login"))

        title = (str(todo.title).strip() if todo.title else "").strip()
        if not title:
            title = f"Todo #{todo.id}"

        calendar_service = CalendarService(current_app.logger)
        result = calendar_service.create_event(
            oauth_client=oauth.google,
            token=token,
            title=title,
            description=todo.description,
            event_date=event_date if not start_dt else None,
            start_time=start_dt,
            end_time=end_dt,
            duration_minutes=todo.duration_minutes or 60,
        )

        if result:
            todo.google_event_id = result.get("id")
            db.session.commit()
            flash("Todo added to Google Calendar!", "success")
        else:
            flash("Failed to create calendar event.", "error")
    except Exception as e:
        flash(f"Error adding to calendar: {str(e)}", "error")
        log_exception(e, message="Quick schedule failed", extra={"todo_id": todo.id})

    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/sync_from_calendar", methods=["POST"])
@login_required
def sync_from_calendar(todo_id):
    """Sync todo description from linked Google Calendar event"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    if not todo.google_event_id:
        flash("This todo is not linked to a calendar event.", "warning")
        return redirect(url_for("todos.list_todos"))

    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService

        token = get_google_token_for_user(current_user)
        if not token:
            flash("You must authenticate with Google first.", "error")
            return redirect(url_for("auth.login"))

        calendar_service = CalendarService(current_app.logger)
        event_data = calendar_service.get_event(
            oauth.google,
            token,
            todo.google_event_id,
        )

        if event_data:
            # Update description from calendar
            new_description = event_data.get("description", "")
            if new_description != todo.description:
                todo.description = new_description
                db.session.commit()
                flash("Description synced from calendar!", "success")
            else:
                flash("Description is already in sync.", "info")
        else:
            flash("Could not fetch calendar event.", "error")
    except Exception as e:
        flash(f"Error syncing from calendar: {str(e)}", "error")
        log_exception(
            e, message="Sync from calendar failed", extra={"todo_id": todo.id}
        )

    return redirect(url_for("todos.list_todos"))
