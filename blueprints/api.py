"""
External API Blueprint - allows external applications to create todos and notes
"""
from datetime import datetime
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import BadRequest

from extensions import db
from models import ApiKey, Note, NoteType, Tag, Todo

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def require_api_key(f):
    """Decorator to require and validate API key authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Invalid or missing API key"}), 401

        key = auth_header[7:]  # Remove "Bearer " prefix
        api_key_obj = ApiKey.verify_key(key)

        if not api_key_obj:
            return jsonify({"error": "Invalid or missing API key"}), 401

        # Check rate limiting
        if api_key_obj.is_rate_limited():
            reset_time = api_key_obj.get_reset_time()
            retry_after = int((reset_time - datetime.utcnow()).total_seconds())
            return (
                jsonify({"error": "Rate limit exceeded", "retry_after": retry_after}),
                429,
            )

        # Record the request
        api_key_obj.record_request()

        # Add rate limit headers
        request.api_key = api_key_obj
        request.rate_limit_remaining = api_key_obj.get_requests_remaining()

        return f(*args, **kwargs)

    return decorated_function


def add_rate_limit_headers(response):
    """Add rate limit headers to response"""
    if hasattr(request, "api_key"):
        response.headers["X-RateLimit-Limit"] = "10"
        response.headers["X-RateLimit-Remaining"] = str(request.rate_limit_remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int(request.api_key.get_reset_time().timestamp())
        )
    return response


@api_bp.after_request
def after_request(response):
    """Add rate limit headers to all API responses"""
    return add_rate_limit_headers(response)


@api_bp.route("/todos", methods=["POST"])
@require_api_key
def create_todo():
    """Create a new todo from external API

    Request body:
    {
        "title": "string (required, max 200)",
        "due_date": "YYYY-MM-DD (optional, defaults to today)",
        "priority": "1-3 (optional, defaults to 2)",
        "tags": ["tag1", "tag2"] (optional),
        "source_app": "string (required)"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify(
                    {
                        "error": "Validation failed",
                        "details": {"body": "Request body must be valid JSON"},
                    }
                ),
                400,
            )

        # Validate required fields
        errors = {}
        title = data.get("title", "").strip()
        source_app = data.get("source_app", "").strip()

        if not title:
            errors["title"] = "Title is required"
        elif len(title) > 200:
            errors["title"] = "Title must be 200 characters or less"

        if not source_app:
            errors["source_app"] = "source_app is required"

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        # Parse optional fields
        due_date = data.get("due_date")
        if due_date:
            try:
                # Parse date from YYYY-MM-DD format
                parts = due_date.split("-")
                if len(parts) != 3:
                    raise ValueError("Invalid format")
                due_date = datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            except (ValueError, TypeError):
                return (
                    jsonify(
                        {
                            "error": "Validation failed",
                            "details": {"due_date": "Must be in YYYY-MM-DD format"},
                        }
                    ),
                    400,
                )
        else:
            # Default to today
            from time_utils import today_local

            due_date = today_local()

        # Validate and parse priority (1-3, default 2)
        priority = data.get("priority", 2)
        try:
            priority = int(priority)
            if priority not in [1, 2, 3]:
                return (
                    jsonify(
                        {
                            "error": "Validation failed",
                            "details": {"priority": "Priority must be 1, 2, or 3"},
                        }
                    ),
                    400,
                )
        except (ValueError, TypeError):
            return (
                jsonify(
                    {
                        "error": "Validation failed",
                        "details": {"priority": "Priority must be an integer"},
                    }
                ),
                400,
            )

        # Map priority numbers to strings (1=low, 2=medium, 3=high)
        priority_map = {1: "low", 2: "medium", 3: "high"}
        priority_str = priority_map[priority]

        # Create the todo
        user = request.api_key.user
        todo = Todo(
            user_id=user.id,
            title=title,
            description=f"Created from {source_app}",
            status="pending",
            priority=priority_str,
            due_date=due_date,
        )
        db.session.add(todo)
        db.session.flush()  # Get the ID without committing

        # Add tags if provided
        from models import add_tag_to_entity

        tags_data = data.get("tags", [])
        if isinstance(tags_data, list):
            for tag_name in tags_data:
                tag_name = str(tag_name).strip()
                if tag_name:
                    # Find or create tag
                    tag = Tag.query.filter_by(user_id=user.id, name=tag_name).first()
                    if not tag:
                        tag = Tag(user_id=user.id, name=tag_name)
                        db.session.add(tag)
                        db.session.flush()

                    # Link tag to todo using polymorphic association
                    add_tag_to_entity(tag, "todo", todo.id)

        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "todo": {
                        "id": todo.id,
                        "title": todo.title,
                        "due_date": todo.due_date.isoformat()
                        if todo.due_date
                        else None,
                        "priority": todo.priority,
                        "description": todo.description,
                    },
                }
            ),
            201,
        )

    except BadRequest as e:
        return jsonify({"error": "Validation failed", "details": {"body": str(e)}}), 400
    except Exception as e:
        current_app.logger.error(f"API error in create_todo: {e}")
        return jsonify({"error": "Internal server error"}), 500


@api_bp.route("/notes", methods=["POST"])
@require_api_key
def create_note():
    """Create a new note from external API

    Request body:
    {
        "title": "string (required, max 200)",
        "type": "string (required, must match existing note type)",
        "content": "string (optional)",
        "source_app": "string (required)"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify(
                    {
                        "error": "Validation failed",
                        "details": {"body": "Request body must be valid JSON"},
                    }
                ),
                400,
            )

        # Validate required fields
        errors = {}
        title = data.get("title", "").strip()
        note_type = data.get("type", "").strip()
        source_app = data.get("source_app", "").strip()

        if not title:
            errors["title"] = "Title is required"
        elif len(title) > 200:
            errors["title"] = "Title must be 200 characters or less"

        if not note_type:
            errors["type"] = "type is required"

        if not source_app:
            errors["source_app"] = "source_app is required"

        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        # Verify note type exists
        user = request.api_key.user
        note_type_obj = NoteType.query.filter_by(
            user_id=user.id, name=note_type
        ).first()

        if not note_type_obj:
            return (
                jsonify(
                    {
                        "error": "Validation failed",
                        "details": {"type": f"Note type '{note_type}' does not exist"},
                    }
                ),
                400,
            )

        # Get content
        content = data.get("content", "").strip()

        # Add date to title based on note type settings
        # Check if note type has date_in_title setting (if it exists)
        from time_utils import today_local

        note_date = today_local()

        # Format title with date (e.g., "Support Request #1234 - 2026-01-26")
        date_str = note_date.strftime("%Y-%m-%d")
        full_title = f"{title} - {date_str}"

        # Append source attribution to content
        if content:
            content = f"{content}\n\n---\nCreated from {source_app}"
        else:
            content = f"Created from {source_app}"

        # Create the note
        note = Note(
            user_id=user.id,
            note_type_id=note_type_obj.id,
            title=full_title,
            content=content,
            created_at=datetime.utcnow(),
        )
        db.session.add(note)
        db.session.commit()

        return (
            jsonify(
                {
                    "success": True,
                    "note": {
                        "id": note.id,
                        "title": note.title,
                        "type": note_type_obj.name,
                    },
                }
            ),
            201,
        )

    except BadRequest as e:
        return jsonify({"error": "Validation failed", "details": {"body": str(e)}}), 400
    except Exception as e:
        current_app.logger.error(f"API error in create_note: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Error handlers for API
@api_bp.errorhandler(404)
def api_not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@api_bp.errorhandler(405)
def api_method_not_allowed(e):
    return jsonify({"error": "Method not allowed"}), 405
