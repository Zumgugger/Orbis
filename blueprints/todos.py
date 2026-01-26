"""
Todos Blueprint - handles all todo/task related routes
"""
from datetime import date, datetime, time, timedelta
from typing import Any

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required

from extensions import db
from models import EntityTag, SharedTitle, Tag, Todo, sync_entity_tags
from time_utils import get_local_tz, now_local, today_local, tomorrow_local
from utilities import get_next_url, log_error, log_exception, log_warning
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

# Work hours for default shared calendar behavior
WORK_HOURS_START = time(7, 0)
WORK_HOURS_END = time(17, 30)


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


def _parse_tag_ids(form_data: str) -> list[int]:
    """Parse tag IDs from form data (comma-separated string)."""
    if not form_data:
        return []
    try:
        return [int(tid.strip()) for tid in form_data.split(",") if tid.strip()]
    except ValueError:
        return []


def _parse_shared_calendar_fields(form: dict, due_time: time | None) -> dict:
    """
    Parse shared calendar fields from form data.

    Args:
        form: Form data dict
        due_time: The todo's scheduled time (for work hours default)

    Returns:
        Dict with sync_to_shared, shared_title
    """
    # Check if user explicitly set sync_to_shared
    sync_to_shared = form.get("sync_to_shared") == "on"

    # Get shared title (from dropdown or custom input)
    shared_title = form.get("shared_title", "").strip()
    custom_title = form.get("shared_title_custom", "").strip()

    if custom_title:
        shared_title = custom_title

    # If no title but sync is enabled, default based on time
    if sync_to_shared and not shared_title:
        if due_time and WORK_HOURS_START <= due_time <= WORK_HOURS_END:
            shared_title = "Work"
        else:
            shared_title = "Busy"

    return {
        "sync_to_shared": sync_to_shared,
        "shared_title": shared_title if sync_to_shared else None,
    }


def _sync_shared_blocks_for_todo(todo: Todo) -> dict[str, Any] | None:
    """
    Sync shared calendar blocks for the date of a todo.

    This should be called after any todo operation that affects shared blocks:
    - Create todo with sync_to_shared=True
    - Update todo (time, shared settings, or completion)
    - Delete todo with sync_to_shared=True

    Returns:
        Sync results dict or None if user has no shared calendar configured
    """
    if not todo.due_date:
        return None

    return _sync_shared_blocks_for_date(todo.due_date)


def _sync_shared_blocks_for_date(sync_date) -> dict[str, Any] | None:
    """
    Sync shared calendar blocks for a specific date.

    Args:
        sync_date: The date to sync blocks for

    Returns:
        Sync results dict or None if user has no shared calendar configured
    """
    if not current_user.shared_calendar_id:
        return None

    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService, SharedBlockService

        token = get_google_token_for_user(current_user)
        if not token:
            return {"errors": ["No OAuth token available"]}

        calendar_service = CalendarService(current_app.logger)
        block_service = SharedBlockService(calendar_service, current_app.logger)

        results = block_service.sync_blocks_for_day(
            current_user,
            sync_date,
            oauth.google,
            token,
        )

        # Flash appropriate messages
        if results["errors"]:
            for error in results["errors"]:
                flash(f"Shared calendar sync error: {error}", "warning")
        elif results["created"] > 0 or results["deleted"] > 0:
            flash("Shared calendar updated", "info")

        return results
    except Exception as e:
        log_exception(e, message="Failed to sync shared blocks")
        return {"errors": [str(e)]}


def _get_shared_titles_for_user() -> list[dict]:
    """Get shared titles for current user, ordered by position."""
    titles = (
        SharedTitle.query.filter_by(user_id=current_user.id)
        .order_by(SharedTitle.position)
        .all()
    )
    return [
        {"id": t.id, "title": t.title, "is_default": t.is_default_work_hours}
        for t in titles
    ]


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
        db.session.flush()  # Get todo.id for tags

        # Sync tags if provided
        tag_ids = data.get("tag_ids", [])
        if tag_ids:
            # Validate tag_ids are integers
            try:
                tag_ids = [int(tid) for tid in tag_ids if tid]
                sync_entity_tags(current_user.id, "todo", todo.id, tag_ids)
            except (ValueError, TypeError):
                pass  # Ignore invalid tag_ids

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

    today = today_local()

    # Get tag filter from query param
    filter_tag_id = request.args.get("tag", type=int)

    # Get all tags for the filter dropdown
    all_tags = (
        Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name.asc()).all()
    )

    # Get the selected tag for display
    selected_tag = None
    if filter_tag_id:
        selected_tag = Tag.query.filter_by(
            id=filter_tag_id, user_id=current_user.id
        ).first()

    # Get all todos for the user
    query = Todo.query.filter_by(user_id=current_user.id)

    # If filtering by tag, join with entity_tags
    if filter_tag_id:
        query = query.join(
            EntityTag,
            (EntityTag.entity_type == "todo") & (EntityTag.entity_id == Todo.id),
        ).filter(EntityTag.tag_id == filter_tag_id)

    todos = query.order_by(Todo.position.asc(), Todo.created_at.desc()).all()

    # Separate into categories:
    # - Overdue: pending todos with due_date before today
    # - Pending: pending todos with due_date today or later (or no due_date)
    # - Completed (today): completed today only (archive old completed)
    overdue = []
    pending = []
    completed = []

    for t in todos:
        if t.status in ("pending", "in_progress"):
            if t.due_date and t.due_date < today:
                overdue.append(t)
            else:
                pending.append(t)
        elif t.status == "completed":
            # Only show completed todos from today (archive old ones)
            if t.completed_at:
                completed_date = t.completed_at.date()
                if completed_date >= today:
                    completed.append(t)
            else:
                # No completed_at timestamp - show it (legacy data)
                completed.append(t)

    return render_template(
        "todos/list.html",
        overdue=overdue,
        pending=pending,
        completed=completed,
        all_tags=all_tags,
        selected_tag=selected_tag,
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
            shared_fields = _parse_shared_calendar_fields(
                request.form, time_fields["due_time"]
            )

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                due_time=time_fields["due_time"],
                end_time=time_fields["end_time"],
                duration_minutes=time_fields["duration_minutes"],
                sync_to_shared=shared_fields["sync_to_shared"],
                shared_title=shared_fields["shared_title"],
                user_id=current_user.id,
            )
            db.session.add(todo)
            db.session.flush()  # Get todo.id for tags

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            if tag_ids:
                sync_entity_tags(current_user.id, "todo", todo.id, tag_ids)

            db.session.commit()

            # Sync shared calendar blocks if needed
            if todo.sync_to_shared and todo.due_date:
                _sync_shared_blocks_for_todo(todo)

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
        shared_titles=_get_shared_titles_for_user(),
        has_shared_calendar=bool(current_user.shared_calendar_id),
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
            shared_fields = _parse_shared_calendar_fields(
                request.form, time_fields["due_time"]
            )

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=preset_date,
                due_time=time_fields["due_time"],
                end_time=time_fields["end_time"],
                duration_minutes=time_fields["duration_minutes"],
                sync_to_shared=shared_fields["sync_to_shared"],
                shared_title=shared_fields["shared_title"],
                user_id=current_user.id,
            )
            db.session.add(todo)
            db.session.flush()  # Get todo.id for tags

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            if tag_ids:
                sync_entity_tags(current_user.id, "todo", todo.id, tag_ids)

            db.session.commit()

            # Sync shared calendar blocks if needed
            if todo.sync_to_shared:
                _sync_shared_blocks_for_todo(todo)

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
        shared_titles=_get_shared_titles_for_user(),
        has_shared_calendar=bool(current_user.shared_calendar_id),
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
            shared_fields = _parse_shared_calendar_fields(
                request.form, time_fields["due_time"]
            )

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=preset_date,
                due_time=time_fields["due_time"],
                end_time=time_fields["end_time"],
                duration_minutes=time_fields["duration_minutes"],
                sync_to_shared=shared_fields["sync_to_shared"],
                shared_title=shared_fields["shared_title"],
                user_id=current_user.id,
            )
            db.session.add(todo)
            db.session.flush()  # Get todo.id for tags

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            if tag_ids:
                sync_entity_tags(current_user.id, "todo", todo.id, tag_ids)

            db.session.commit()

            # Sync shared calendar blocks if needed
            if todo.sync_to_shared:
                _sync_shared_blocks_for_todo(todo)

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
        shared_titles=_get_shared_titles_for_user(),
        has_shared_calendar=bool(current_user.shared_calendar_id),
    )


@todos_bp.route("/<int:todo_id>/edit", methods=["GET", "POST"])
@login_required
def edit_todo(todo_id):
    """Edit an existing todo"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    # Track if we need to update shared calendar (date or sync status changed)
    old_due_date = todo.due_date
    old_sync_to_shared = todo.sync_to_shared

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

            # Handle shared calendar fields
            shared_fields = _parse_shared_calendar_fields(
                request.form, time_fields["due_time"]
            )
            todo.sync_to_shared = shared_fields["sync_to_shared"]
            todo.shared_title = shared_fields["shared_title"]

            # Mark as in progress when edited (per tests expectation)
            if todo.status == "pending":
                todo.status = "in_progress"

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            sync_entity_tags(current_user.id, "todo", todo.id, tag_ids)

            db.session.commit()

            # Sync with Google Calendar if linked
            if todo.google_event_id:
                _sync_todo_to_calendar(todo)

            # Handle shared calendar sync
            dates_to_sync = set()

            # If was synced but now isn't, or date changed, need to update old date
            if old_sync_to_shared and old_due_date:
                if not todo.sync_to_shared or todo.due_date != old_due_date:
                    dates_to_sync.add(old_due_date)

            # If currently synced, always update that date (time/title changes affect blocks)
            if todo.sync_to_shared and todo.due_date:
                dates_to_sync.add(todo.due_date)

            # Sync all affected dates
            for sync_date in dates_to_sync:
                _sync_shared_blocks_for_date(sync_date)

            flash("Todo updated successfully!", "success")
            return redirect(url_for("todos.list_todos"))
        except ValidationError as e:
            flash(str(e), "error")
            log_warning(
                "Validation error editing todo",
                extra={"todo_id": todo_id, "error": str(e)},
            )
            return render_template(
                "todos/form.html",
                todo=todo,
                action="Edit",
                shared_titles=_get_shared_titles_for_user(),
                has_shared_calendar=bool(current_user.shared_calendar_id),
            )

    return render_template(
        "todos/form.html",
        todo=todo,
        action="Edit",
        shared_titles=_get_shared_titles_for_user(),
        has_shared_calendar=bool(current_user.shared_calendar_id),
    )


@todos_bp.route("/<int:todo_id>/toggle", methods=["POST"])
@login_required
def toggle_todo(todo_id):
    """Toggle todo completion status and sync with Google Calendar if linked"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    is_ajax = (
        request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json
    )

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

    # Recalculate shared blocks if todo affects shared calendar
    # (completed todos may be removed from future blocks)
    if todo.sync_to_shared and todo.due_date:
        _sync_shared_blocks_for_todo(todo)

    if is_ajax:
        return jsonify(
            {
                "success": True,
                "status": todo.status,
                "completed": todo.status == "completed",
            }
        )

    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
    return redirect(url_for("todos.list_todos"))


def _parse_single_event(event_data: dict) -> dict:
    """Parse a single event from Google Calendar API response."""
    from datetime import datetime as dt

    start = event_data.get("start", {})
    end = event_data.get("end", {})

    # Check if all-day event
    all_day = "date" in start and "dateTime" not in start

    start_dt = None
    end_dt = None
    start_raw = None
    end_raw = None

    if all_day:
        start_raw = start.get("date")
        end_raw = end.get("date")
        # Don't parse to datetime for all-day events - keep as raw date string
    else:
        start_str = start.get("dateTime")
        end_str = end.get("dateTime")
        start_raw = start_str
        end_raw = end_str
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
        "start_raw": start_raw,
        "end_raw": end_raw,
        "all_day": all_day,
    }


def _sync_calendar_events_to_todos() -> None:
    """Sync Google Calendar events to todos - create, update, and handle deletions."""
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
        # Fetch events for today and tomorrow (for creating NEW todos only)
        calendar_events = calendar_service.fetch_events_for_user(
            current_user,
            today,
            today + timedelta(days=2),
            get_google_token_for_user,
            oauth.google,
        )

        # Build a map of event_id -> event data
        events_by_id = {ev.get("id"): ev for ev in calendar_events if ev.get("id")}

        # Get ALL existing todos linked to calendar events (regardless of date)
        linked_todos = Todo.query.filter(
            Todo.user_id == current_user.id,
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
                # Event not in 2-day window - fetch it individually to check if still exists
                event_data = calendar_service.get_event(
                    oauth.google, token, todo.google_event_id
                )
                if event_data:
                    # Check if event is cancelled
                    if event_data.get("status") == "cancelled":
                        log_warning(
                            f"Deleting todo {todo.id} - calendar event was cancelled"
                        )
                        db.session.delete(todo)
                    else:
                        # Event exists - parse and update todo
                        event = _parse_single_event(event_data)
                        _update_todo_from_event(todo, event, today)
                else:
                    # Event was deleted from calendar - delete the todo
                    log_warning(f"Deleting todo {todo.id} - calendar event not found")
                    db.session.delete(todo)

        # Create todos for NEW events within the 2-day window only
        for event in calendar_events:
            event_id = event.get("id")
            if not event_id or event_id in existing_event_ids:
                continue

            # Parse event times
            start_dt = event.get("start_dt")
            is_all_day = event.get("all_day", False)

            # For all-day events, parse the date from start_raw (format: YYYY-MM-DD)
            if is_all_day:
                start_raw = event.get("start_raw")
                if start_raw:
                    due_date = date.fromisoformat(start_raw)
                else:
                    due_date = today
                due_time = None
            else:
                due_date = start_dt.date() if start_dt else today
                due_time = start_dt.time() if start_dt else None

            end_dt = event.get("end_dt")
            end_time = end_dt.time() if end_dt and not is_all_day else None

            # Calculate duration
            duration_minutes = None
            if start_dt and end_dt and not is_all_day:
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


def _update_todo_from_event(todo: Todo, event: dict, today) -> None:
    """Update a todo's fields from a calendar event if changed."""
    # Update title if changed (but not if user customized it)
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

    if is_all_day:
        # For all-day events, parse date from start_raw
        start_raw = event.get("start_raw")
        if start_raw:
            new_due_date = date.fromisoformat(start_raw)
            if todo.due_date != new_due_date:
                todo.due_date = new_due_date
        todo.due_time = None
        todo.end_time = None
    elif start_dt:
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

    # Capture info for shared calendar sync before deletion
    sync_to_shared = todo.sync_to_shared
    due_date = todo.due_date
    google_event_id = todo.google_event_id

    # Delete Google Calendar event if linked
    if google_event_id:
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
                    google_event_id,
                )
        except Exception as e:
            log_warning(
                f"Failed to delete calendar event on todo deletion: {e}",
                extra={"todo_id": todo.id, "event_id": google_event_id},
            )

    db.session.delete(todo)
    db.session.commit()

    # Recalculate shared blocks after deletion
    if sync_to_shared and due_date:
        _sync_shared_blocks_for_date(due_date)

    flash("Todo deleted successfully!", "success")
    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/due/today", methods=["POST"])
@login_required
def set_due_today(todo_id):
    """Set todo due date to today"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    # Track old date for shared calendar sync
    old_due_date = todo.due_date

    todo.due_date = date.today()
    db.session.commit()

    # Handle shared calendar sync if needed
    if todo.sync_to_shared:
        dates_to_sync = {todo.due_date}
        if old_due_date and old_due_date != todo.due_date:
            dates_to_sync.add(old_due_date)
        for sync_date in dates_to_sync:
            _sync_shared_blocks_for_date(sync_date)

    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
    return redirect(url_for("todos.list_todos"))


@todos_bp.route("/<int:todo_id>/due/tomorrow", methods=["POST"])
@login_required
def set_due_tomorrow(todo_id):
    """Set todo due date to tomorrow"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    # Track old date for shared calendar sync
    old_due_date = todo.due_date

    todo.due_date = date.today() + timedelta(days=1)
    db.session.commit()

    # Handle shared calendar sync if needed
    if todo.sync_to_shared:
        dates_to_sync = {todo.due_date}
        if old_due_date and old_due_date != todo.due_date:
            dates_to_sync.add(old_due_date)
        for sync_date in dates_to_sync:
            _sync_shared_blocks_for_date(sync_date)

    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
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


@todos_bp.route("/<int:todo_id>/reschedule_calendar", methods=["POST"])
@login_required
def reschedule_calendar(todo_id):
    """Reschedule a todo's linked Google Calendar event to a new date/time"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    if not todo.google_event_id:
        flash("This todo is not linked to a calendar event.", "warning")
        return redirect(get_next_url("todos.list_todos"))

    try:
        event_date = validate_date(request.form.get("event_date"), required=True)
        event_time = validate_time(request.form.get("event_time"))
        duration_hours, duration_minutes = validate_duration(
            request.form.get("duration_hours"), request.form.get("duration_minutes")
        )
    except ValidationError as e:
        flash(str(e), "error")
        log_warning(
            "Validation error rescheduling todo",
            extra={"todo_id": todo.id, "error": str(e)},
        )
        return redirect(get_next_url("todos.list_todos"))

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

    try:
        from flask import current_app

        from blueprints.auth import get_google_token_for_user, oauth
        from services import CalendarService

        token = get_google_token_for_user(current_user)
        if not token:
            flash("You must authenticate with Google first.", "error")
            return redirect(url_for("auth.login"))

        calendar_service = CalendarService(current_app.logger)
        result = calendar_service.update_event(
            oauth_client=oauth.google,
            token=token,
            event_id=todo.google_event_id,
            start_time=start_dt,
            end_time=end_dt,
            event_date=event_date if not start_dt else None,
        )

        if result == "token_invalid":
            flash("Your Google session has expired. Please reconnect.", "warning")
            session["next"] = url_for("todos.list_todos")
            return redirect(url_for("auth.login"))
        elif result:
            # Update todo's time fields to match new schedule
            todo.due_date = event_date
            todo.due_time = event_time
            if end_dt:
                todo.end_time = end_dt.time()
            todo.duration_minutes = (duration_hours * 60) + duration_minutes
            db.session.commit()
            flash("Calendar event rescheduled!", "success")
        else:
            flash("Failed to update calendar event.", "error")
            log_error(
                "CalendarService.update_event returned False",
                extra={"todo_id": todo.id, "event_id": todo.google_event_id},
            )
    except Exception as e:
        flash(f"Error rescheduling event: {str(e)}", "error")
        log_exception(
            e,
            message="Exception rescheduling calendar event",
            extra={"todo_id": todo.id},
        )

    return redirect(get_next_url("todos.list_todos"))


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

        if result and result.get("id"):
            todo.google_event_id = result.get("id")
            db.session.commit()
            html_link = result.get("htmlLink", "")
            if html_link:
                flash(
                    f'Todo added to Google Calendar! <a href="{html_link}" target="_blank">View event</a>',
                    "success",
                )
            else:
                flash("Todo added to Google Calendar!", "success")
        elif result and result.get("error") == "token_invalid":
            flash("Your Google session has expired. Please reconnect.", "warning")
            session["next"] = url_for("todos.list_todos")
            return redirect(url_for("auth.login"))
        else:
            flash(
                "Failed to create calendar event. Try reconnecting your Google account.",
                "error",
            )
            session["next"] = url_for("todos.list_todos")
            return redirect(url_for("auth.login"))
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
