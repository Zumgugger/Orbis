"""
Todos Blueprint - handles all todo/task related routes
"""
import os
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
    validate_priority,
    validate_text,
    validate_time,
    validate_title,
)

todos_bp = Blueprint("todos", __name__, url_prefix="/todos")


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
    """Display all todos"""
    todos = (
        Todo.query.filter_by(user_id=current_user.id)
        .order_by(Todo.position.asc(), Todo.created_at.desc())
        .all()
    )
    pending = [t for t in todos if t.status in ("pending", "in_progress")]
    completed = [t for t in todos if t.status == "completed"]
    return render_template("todos/list.html", pending=pending, completed=completed)


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

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
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

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=preset_date,
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

            todo = Todo(
                title=title,
                description=description,
                priority=priority,
                due_date=preset_date,
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

            # Mark as in progress when edited (per tests expectation)
            if todo.status == "pending":
                todo.status = "in_progress"
            db.session.commit()
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
    """Toggle todo completion status"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

    if todo.status == "pending":
        todo.status = "completed"
        todo.completed_at = datetime.utcnow()
    else:
        todo.status = "pending"
        todo.completed_at = None

    db.session.commit()
    next_page = request.args.get("next")
    if next_page:
        return redirect(next_page)
    return redirect(url_for("todos.list_todos"))


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
    """Schedule a todo as a Google Calendar event"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()

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
        end_dt = start_dt + timedelta(hours=duration_hours, minutes=duration_minutes)
    else:
        # All-day event
        start_dt = None
        end_dt = None

    # Call Google Calendar API
    try:
        from blueprints.auth import get_google_token_for_user

        token = get_google_token_for_user(current_user)
        if not token:
            flash("You must authenticate with Google first.", "error")
            log_warning("Missing Google auth token", extra={"todo_id": todo.id})
            return redirect(url_for("auth.login"))

        tz = os.getenv("DEFAULT_TIMEZONE", "Europe/Zurich")
        title = (str(todo.title).strip() if todo.title else "").strip()
        if not title:
            title = f"Todo #{todo.id}"
        event = {"summary": title, "description": (todo.description or "")}
        if start_dt and end_dt:
            event["start"] = {"dateTime": start_dt.isoformat(), "timeZone": tz}
            event["end"] = {"dateTime": end_dt.isoformat(), "timeZone": tz}
        else:
            event["start"] = {"date": event_date.isoformat()}
            event["end"] = {"date": (event_date + timedelta(days=1)).isoformat()}

        # Use Authlib client to handle token/refresh
        from blueprints.auth import oauth

        # Debug: log outgoing event structure
        try:
            from flask import current_app

            current_app.logger.info(
                f"Creating calendar event for todo {todo.id}: {event}"
            )
        except Exception:
            pass

        response = oauth.google.post(
            "https://www.googleapis.com/calendar/v3/calendars/primary/events",
            json=event,
            token=token,
        )

        if response.status_code in (200, 201):
            flash("Todo scheduled in Google Calendar!", "success")
        else:
            try:
                err = response.json()
            except Exception:
                err = response.text
            flash(f"Failed to schedule: {err}", "error")
            log_error(
                "Failed to schedule calendar event",
                extra={
                    "todo_id": todo.id,
                    "status_code": response.status_code,
                    "response": err,
                },
            )
    except Exception as e:
        flash(f"Error scheduling event: {str(e)}", "error")
        log_exception(
            e, message="Exception scheduling calendar event", extra={"todo_id": todo.id}
        )

    return redirect(url_for("todos.list_todos"))
