"""
Ideas Blueprint - handles idea management with notes, mindmaps, and files
"""
import os
from datetime import datetime

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.orm import load_only, selectinload

from extensions import db
from file_security import (
    FileSecurityError,
    delete_uploaded_file,
    get_file_path,
    save_uploaded_file,
)
from models import Idea, IdeaFile
from utilities import log_exception, log_warning
from validation import ValidationError, validate_text, validate_title

ideas_bp = Blueprint("ideas", __name__, url_prefix="/ideas")


@ideas_bp.route("/")
@login_required
def list_ideas():
    """List all ideas"""
    ideas = (
        Idea.query.options(
            load_only(
                Idea.id,
                Idea.title,
                Idea.description,
                Idea.updated_at,
                Idea.mindmap_data,
                Idea.notes,
            ),
            selectinload(Idea.files).load_only(IdeaFile.id),
        )
        .filter_by(user_id=current_user.id)
        .order_by(Idea.position.asc(), Idea.updated_at.desc())
        .all()
    )
    return render_template("ideas/list.html", ideas=ideas)


@ideas_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_idea():
    """Create a new idea"""
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            description = validate_text(
                request.form.get("description"), max_length=5000
            )
            category = request.form.get("category") or None

            idea = Idea(
                title=title,
                description=description,
                category=category,
                user_id=current_user.id,
            )
            db.session.add(idea)
            db.session.commit()

            flash("Idea created successfully!", "success")
            return redirect(url_for("ideas.view_idea", idea_id=idea.id))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("ideas/form.html", idea=None)

    return render_template("ideas/form.html", idea=None)


@ideas_bp.route("/<int:idea_id>", methods=["GET", "POST"])
@login_required
def view_idea(idea_id):
    """View and edit an idea - unified endpoint"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        try:
            idea.title = validate_title(request.form.get("title"), max_length=200)
            idea.description = validate_text(
                request.form.get("description"), max_length=5000
            )
            idea.updated_at = datetime.utcnow()
            db.session.commit()

            flash("Idea updated successfully!", "success")
            return redirect(url_for("ideas.view_idea", idea_id=idea.id))
        except ValidationError as e:
            flash(str(e), "error")

    return render_template("ideas/view.html", idea=idea)


@ideas_bp.route("/<int:idea_id>/edit", methods=["GET", "POST"])
@login_required
def edit_idea(idea_id):
    """Backward-compatibility redirect to unified view endpoint"""
    return view_idea(idea_id)


@ideas_bp.route("/<int:idea_id>/delete", methods=["POST"])
@login_required
def delete_idea(idea_id):
    """Delete an idea"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()

    # Delete associated files
    for file in idea.files:
        try:
            if file.file_path and os.path.exists(file.file_path):
                os.remove(file.file_path)
        except Exception:
            pass

    db.session.delete(idea)
    db.session.commit()

    flash("Idea deleted successfully!", "success")
    return redirect(url_for("ideas.list_ideas"))


@ideas_bp.route("/<int:idea_id>/notes", methods=["POST"])
@login_required
def save_notes(idea_id):
    """Save markdown notes for an idea"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()

        # Accept both form and JSON payloads
        notes = request.form.get("notes") or (request.get_json(silent=True) or {}).get(
            "notes"
        )
        notes = validate_text(notes, field_name="Notes", max_length=100000)
        idea.notes = notes
        idea.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "message": "Notes saved successfully"})
    except ValidationError as e:
        log_warning(
            "Validation error saving notes", extra={"idea_id": idea_id, "error": str(e)}
        )
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        db.session.rollback()
        log_exception(e, message="Failed to save notes", extra={"idea_id": idea_id})
        return jsonify({"success": False, "error": "Failed to save notes"}), 500


# Backward-compatibility alias: older UI may call /save_notes
@ideas_bp.route("/<int:idea_id>/save_notes", methods=["POST"])
@login_required
def save_notes_alias(idea_id):
    return save_notes(idea_id)


@ideas_bp.route("/<int:idea_id>/mindmap", methods=["POST"])
@login_required
def save_mindmap(idea_id):
    """Save mindmap data for an idea"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()

        payload = request.get_json(silent=True) or {}
        mindmap_data = payload.get("mindmap_data") or request.form.get("mindmap_data")
        if not mindmap_data:
            return jsonify({"success": False, "error": "No mindmap data provided"}), 400

        # Store exactly the provided mindmap data string to match test expectations
        idea.mindmap_data = mindmap_data
        idea.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "message": "Mindmap saved successfully"})
    except Exception as e:
        db.session.rollback()
        log_exception(e, message="Failed to save mindmap", extra={"idea_id": idea_id})
        return jsonify({"success": False, "error": "Failed to save mindmap"}), 500


@ideas_bp.route("/<int:idea_id>/upload", methods=["POST"])
@login_required
def upload_file(idea_id):
    """Upload a file attachment with security validation"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()

        if "file" not in request.files:
            return jsonify({"success": False, "error": "No file provided"}), 400

        file = request.files["file"]
        if not file or file.filename == "":
            return jsonify({"success": False, "error": "No file selected"}), 400

        # Use secure file upload with validation
        try:
            file_metadata = save_uploaded_file(file, file.filename)
        except FileSecurityError as e:
            log_warning(
                "File security error on upload",
                extra={"idea_id": idea_id, "error": str(e)},
            )
            return jsonify({"success": False, "error": str(e)}), 400

        # Save to database
        idea_file = IdeaFile(
            idea_id=idea.id,
            original_filename=file_metadata.get("original_filename") or file.filename,
            stored_filename=file_metadata.get("stored_filename")
            or file_metadata.get("filename"),
            file_path=file_metadata.get("file_path") or file_metadata.get("filepath"),
            file_size=file_metadata.get("file_size") or file_metadata.get("filesize"),
            mime_type=file_metadata.get("mime_type"),
        )
        db.session.add(idea_file)
        idea.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "File uploaded successfully",
                "file": {
                    "id": idea_file.id,
                    "filename": idea_file.original_filename,
                    "filesize": idea_file.file_size,
                    "uploaded_at": idea_file.uploaded_at.isoformat(),
                },
            }
        )
    except Exception as e:
        db.session.rollback()
        log_exception(e, message="Failed to upload file", extra={"idea_id": idea_id})
        return jsonify({"success": False, "error": "Failed to upload file"}), 500


@ideas_bp.route("/<int:idea_id>/delete_file/<int:file_id>", methods=["POST"])
@login_required
def delete_file(idea_id, file_id):
    """Delete a file attachment with path validation"""
    try:
        idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
        idea_file = IdeaFile.query.filter_by(id=file_id, idea_id=idea.id).first_or_404()

        # Securely delete physical file
        try:
            delete_uploaded_file(idea_file.file_path or idea_file.filepath)
        except Exception as exc:
            # Ignore but log file deletion errors (file may not exist or legacy path invalid)
            log_warning(
                "Delete file physical path failed",
                extra={"file_id": file_id, "idea_id": idea_id, "error": str(exc)},
            )

        db.session.delete(idea_file)
        idea.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "message": "File deleted successfully"})
    except Exception as e:
        db.session.rollback()
        log_exception(
            e,
            message="Failed to delete file",
            extra={"file_id": file_id, "idea_id": idea_id},
        )
        return jsonify({"success": False, "error": "Failed to delete file"}), 500


@ideas_bp.route("/files/<int:file_id>/delete", methods=["POST"])
@login_required
def delete_file_simple(file_id):
    """Delete a file attachment using file_id only (route expected by tests)."""
    try:
        idea_file = db.session.get(IdeaFile, file_id)
        if idea_file is None:
            abort(404)
        # Ensure the file belongs to the current user
        idea = Idea.query.filter_by(
            id=idea_file.idea_id, user_id=current_user.id
        ).first_or_404()

        try:
            delete_uploaded_file(idea_file.file_path or idea_file.filepath)
        except Exception as exc:
            log_warning(
                "Delete file (simple) physical path failed",
                extra={"file_id": file_id, "idea_id": idea.id, "error": str(exc)},
            )

        db.session.delete(idea_file)
        idea.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "message": "File deleted successfully"})
    except Exception as e:
        db.session.rollback()
        log_exception(
            e, message="Failed to delete file (simple)", extra={"file_id": file_id}
        )
        return jsonify({"success": False, "error": "Failed to delete file"}), 500


@ideas_bp.route("/<int:idea_id>/download_file/<int:file_id>")
@login_required
def download_file(idea_id, file_id):
    """Download a file attachment with path validation"""
    idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first_or_404()
    idea_file = IdeaFile.query.filter_by(id=file_id, idea_id=idea.id).first_or_404()

    try:
        # Get validated file path
        path = idea_file.file_path or idea_file.filepath
        name = idea_file.original_filename or idea_file.stored_filename
        validated_path = get_file_path(path)
        return send_file(validated_path, as_attachment=True, download_name=name)
    except FileSecurityError as e:
        flash(f"Security error: {str(e)}", "error")
        log_warning(
            "File security error on download",
            extra={"idea_id": idea_id, "file_id": file_id, "error": str(e)},
        )
        return redirect(url_for("ideas.view_idea", idea_id=idea.id))
    except Exception:
        flash("File not found", "error")
        log_warning(
            "File not found on download", extra={"idea_id": idea_id, "file_id": file_id}
        )
        return redirect(url_for("ideas.view_idea", idea_id=idea.id))


@ideas_bp.route("/reorder", methods=["POST"])
@login_required
def reorder():
    """Persist drag-and-drop order of ideas for the current user"""
    payload = request.get_json(silent=True) or {}
    order = payload.get("order", [])
    if not isinstance(order, list):
        return {"success": False, "error": "Invalid order payload"}, 400

    try:
        for position, idea_id in enumerate(order):
            idea = Idea.query.filter_by(id=idea_id, user_id=current_user.id).first()
            if idea:
                idea.position = position
        db.session.commit()
        return {"success": True}, 200
    except Exception:
        db.session.rollback()
        return {"success": False, "error": "Failed to persist order"}, 500
