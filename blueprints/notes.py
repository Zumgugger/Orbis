"""
Notes Blueprint - handles notes with custom type tabs
"""
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import EntityTag, Note, NoteType, Tag, get_tags_for_entity, sync_entity_tags
from utilities import sanitize_html
from validation import ValidationError, validate_title


def _parse_tag_ids(form_value: str) -> list[int]:
    """Parse comma-separated tag IDs from form input."""
    if not form_value:
        return []
    return [int(tid) for tid in form_value.split(",") if tid.strip().isdigit()]


notes_bp = Blueprint("notes", __name__, url_prefix="/notes")


@notes_bp.route("/")
@login_required
def list_notes():
    """List all notes - All Notes tab"""
    type_id = request.args.get("type", "")
    search_q = request.args.get("q", "").strip()
    filter_tag_id = request.args.get("tag", type=int)

    # Get or create user's note types
    note_types = NoteType.get_or_create_defaults(current_user.id)

    # Get all tags for filter dropdown
    all_tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()

    # Get selected tag for display
    selected_tag = None
    if filter_tag_id:
        selected_tag = Tag.query.filter_by(
            id=filter_tag_id, user_id=current_user.id
        ).first()

    query = Note.query.filter_by(user_id=current_user.id)

    if type_id:
        query = query.filter_by(note_type_id=int(type_id))

    # Filter by tag if specified
    if filter_tag_id:
        query = query.join(
            EntityTag,
            (EntityTag.entity_type == "note") & (EntityTag.entity_id == Note.id),
        ).filter(EntityTag.tag_id == filter_tag_id)

    if search_q:
        query = query.filter(
            db.or_(
                Note.title.ilike(f"%{search_q}%"),
                Note.content.ilike(f"%{search_q}%"),
            )
        )

    notes = query.order_by(Note.pinned.desc(), Note.updated_at.desc()).all()

    # Get tags for all notes
    note_tags = {}
    for note in notes:
        note_tags[note.id] = get_tags_for_entity(current_user.id, "note", note.id)

    return render_template(
        "notes/list.html",
        notes=notes,
        note_types=note_types,
        note_tags=note_tags,
        all_tags=all_tags,
        selected_tag=selected_tag,
        current_type_id=type_id,
        search_q=search_q,
        active_tab="all",
    )


@notes_bp.route("/type/<int:type_id>")
@login_required
def list_by_type(type_id):
    """List notes filtered by a specific type tab"""
    search_q = request.args.get("q", "").strip()
    filter_tag_id = request.args.get("tag", type=int)

    note_type = NoteType.query.filter_by(
        id=type_id, user_id=current_user.id
    ).first_or_404()

    note_types = (
        NoteType.query.filter_by(user_id=current_user.id)
        .order_by(NoteType.position)
        .all()
    )

    # Get all tags for filter dropdown
    all_tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()

    # Get selected tag for display
    selected_tag = None
    if filter_tag_id:
        selected_tag = Tag.query.filter_by(
            id=filter_tag_id, user_id=current_user.id
        ).first()

    query = Note.query.filter_by(user_id=current_user.id, note_type_id=type_id)

    # Filter by tag if specified
    if filter_tag_id:
        query = query.join(
            EntityTag,
            (EntityTag.entity_type == "note") & (EntityTag.entity_id == Note.id),
        ).filter(EntityTag.tag_id == filter_tag_id)

    if search_q:
        query = query.filter(
            db.or_(
                Note.title.ilike(f"%{search_q}%"),
                Note.content.ilike(f"%{search_q}%"),
            )
        )

    notes = query.order_by(Note.pinned.desc(), Note.updated_at.desc()).all()

    # Get tags for all notes
    note_tags = {}
    for note in notes:
        note_tags[note.id] = get_tags_for_entity(current_user.id, "note", note.id)

    return render_template(
        "notes/list.html",
        notes=notes,
        note_types=note_types,
        note_tags=note_tags,
        all_tags=all_tags,
        selected_tag=selected_tag,
        current_type_id=str(type_id),
        current_note_type=note_type,
        search_q=search_q,
        active_tab=type_id,
    )


@notes_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_note():
    """Create a new note"""
    # Get or create user's note types
    note_types = NoteType.get_or_create_defaults(current_user.id)

    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            content = sanitize_html(request.form.get("content", ""))
            note_type_id = request.form.get("note_type_id") or None
            entry_date_str = request.form.get("entry_date")

            entry_date = None
            if entry_date_str:
                try:
                    entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            note = Note(
                title=title,
                content=content,
                note_type_id=int(note_type_id) if note_type_id else None,
                entry_date=entry_date,
                user_id=current_user.id,
            )
            db.session.add(note)
            db.session.commit()

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            if tag_ids:
                sync_entity_tags(current_user.id, "note", note.id, tag_ids)
                db.session.commit()

            flash("Note created successfully!", "success")

            # Redirect to the note's type tab if set, otherwise all notes
            if note_type_id:
                return redirect(url_for("notes.list_by_type", type_id=note_type_id))
            return redirect(url_for("notes.list_notes"))

        except ValidationError as e:
            flash(str(e), "error")

    # Pre-fill type from query param
    preset_type_id = request.args.get("type_id", "")
    preset_date = request.args.get("date", "")

    return render_template(
        "notes/form.html",
        note=None,
        action="Create",
        note_types=note_types,
        preset_type_id=preset_type_id,
        preset_date=preset_date,
    )


@notes_bp.route("/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    """Edit an existing note"""
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    note_types = (
        NoteType.query.filter_by(user_id=current_user.id)
        .order_by(NoteType.position)
        .all()
    )

    if request.method == "POST":
        try:
            note.title = validate_title(request.form.get("title"), max_length=200)
            note.content = sanitize_html(request.form.get("content", ""))
            note_type_id = request.form.get("note_type_id")
            note.note_type_id = int(note_type_id) if note_type_id else None

            entry_date_str = request.form.get("entry_date")
            if entry_date_str:
                try:
                    note.entry_date = datetime.strptime(
                        entry_date_str, "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass
            else:
                note.entry_date = None

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            sync_entity_tags(current_user.id, "note", note.id, tag_ids)

            db.session.commit()
            flash("Note updated successfully!", "success")

            # Redirect to the note's type tab if set, otherwise all notes
            if note.note_type_id:
                return redirect(
                    url_for("notes.list_by_type", type_id=note.note_type_id)
                )
            return redirect(url_for("notes.list_notes"))

        except ValidationError as e:
            flash(str(e), "error")

    return render_template(
        "notes/form.html",
        note=note,
        action="Edit",
        note_types=note_types,
        preset_type_id=str(note.note_type_id) if note.note_type_id else "",
        preset_date=note.entry_date.isoformat() if note.entry_date else "",
    )


@notes_bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    """Delete a note"""
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    note_type_id = note.note_type_id
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted successfully!", "success")

    if note_type_id:
        return redirect(url_for("notes.list_by_type", type_id=note_type_id))
    return redirect(url_for("notes.list_notes"))


@notes_bp.route("/<int:note_id>/toggle_pin", methods=["POST"])
@login_required
def toggle_pin(note_id):
    """Toggle pinned status"""
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    note.pinned = not note.pinned
    db.session.commit()
    return redirect(request.referrer or url_for("notes.list_notes"))


# ---- Note Types Management ----
@notes_bp.route("/types")
@login_required
def manage_types():
    """Manage note types (tabs)"""
    note_types = NoteType.get_or_create_defaults(current_user.id)
    return render_template("notes/types.html", note_types=note_types)


@notes_bp.route("/types/create", methods=["POST"])
@login_required
def create_type():
    """Create a new note type"""
    name = request.form.get("name", "").strip()
    icon = request.form.get("icon", "bi-file-text").strip()

    if not name:
        flash("Type name is required.", "error")
        return redirect(url_for("notes.manage_types"))

    if len(name) > 50:
        flash("Type name too long (max 50 chars).", "error")
        return redirect(url_for("notes.manage_types"))

    # Check for duplicate name
    existing = NoteType.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        flash("A type with that name already exists.", "error")
        return redirect(url_for("notes.manage_types"))

    # Get max position
    max_pos = (
        db.session.query(db.func.max(NoteType.position))
        .filter_by(user_id=current_user.id)
        .scalar()
        or 0
    )

    note_type = NoteType(
        name=name,
        icon=icon,
        position=max_pos + 1,
        user_id=current_user.id,
    )
    db.session.add(note_type)
    db.session.commit()
    flash("Note type created!", "success")
    return redirect(url_for("notes.manage_types"))


@notes_bp.route("/types/<int:type_id>/edit", methods=["POST"])
@login_required
def edit_type(type_id):
    """Edit a note type"""
    note_type = NoteType.query.filter_by(
        id=type_id, user_id=current_user.id
    ).first_or_404()

    name = request.form.get("name", "").strip()
    icon = request.form.get("icon", note_type.icon).strip()

    if not name:
        flash("Type name is required.", "error")
        return redirect(url_for("notes.manage_types"))

    if len(name) > 50:
        flash("Type name too long (max 50 chars).", "error")
        return redirect(url_for("notes.manage_types"))

    # Check for duplicate name (excluding self)
    existing = NoteType.query.filter(
        NoteType.user_id == current_user.id,
        NoteType.name == name,
        NoteType.id != type_id,
    ).first()
    if existing:
        flash("A type with that name already exists.", "error")
        return redirect(url_for("notes.manage_types"))

    note_type.name = name
    note_type.icon = icon
    db.session.commit()
    flash("Note type updated!", "success")
    return redirect(url_for("notes.manage_types"))


@notes_bp.route("/types/<int:type_id>/delete", methods=["POST"])
@login_required
def delete_type(type_id):
    """Delete a note type"""
    note_type = NoteType.query.filter_by(
        id=type_id, user_id=current_user.id
    ).first_or_404()

    # Remove type from notes (don't delete notes)
    Note.query.filter_by(note_type_id=type_id).update({"note_type_id": None})
    db.session.delete(note_type)
    db.session.commit()
    flash("Note type deleted!", "success")
    return redirect(url_for("notes.manage_types"))
