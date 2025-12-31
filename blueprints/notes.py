"""
Notes Blueprint - handles notes and journaling
"""
from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import Note, NoteCategory
from validation import ValidationError, validate_title

notes_bp = Blueprint("notes", __name__, url_prefix="/notes")

# Built-in prompts
DAILY_PROMPTS = [
    "What are you grateful for today?",
    "What's the most important thing you want to accomplish?",
    "How are you feeling right now?",
    "What's one thing you learned recently?",
    "What challenge are you facing?",
]

WEEKLY_PROMPTS = [
    "What went well this week?",
    "What was challenging?",
    "What will you do differently next week?",
    "What are your top 3 wins?",
    "What are you looking forward to?",
]


def get_week_start(d: date) -> date:
    """Get Monday of the week containing date d"""
    return d - timedelta(days=d.weekday())


@notes_bp.route("/")
@login_required
def list_notes():
    """List all notes with filtering"""
    note_type = request.args.get("type", "")
    category_id = request.args.get("category", "")
    search_q = request.args.get("q", "").strip()

    query = Note.query.filter_by(user_id=current_user.id)

    if note_type:
        query = query.filter_by(note_type=note_type)
    if category_id:
        query = query.filter_by(category_id=int(category_id))
    if search_q:
        query = query.filter(
            db.or_(
                Note.title.ilike(f"%{search_q}%"),
                Note.content.ilike(f"%{search_q}%"),
            )
        )

    notes = query.order_by(Note.pinned.desc(), Note.updated_at.desc()).all()
    categories = NoteCategory.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "notes/list.html",
        notes=notes,
        categories=categories,
        note_types=Note.TYPES,
        current_type=note_type,
        current_category=category_id,
        search_q=search_q,
    )


@notes_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_note():
    """Create a new note"""
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            content = request.form.get("content", "")
            note_type = request.form.get("note_type", Note.TYPE_JOURNAL)
            category_id = request.form.get("category_id") or None
            entry_date_str = request.form.get("entry_date")

            entry_date = None
            if entry_date_str:
                try:
                    entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # Default entry_date for journal/weekly types
            if note_type == Note.TYPE_JOURNAL and not entry_date:
                entry_date = date.today()
            elif note_type == Note.TYPE_WEEKLY and not entry_date:
                entry_date = get_week_start(date.today())

            note = Note(
                title=title,
                content=content,
                note_type=note_type,
                category_id=int(category_id) if category_id else None,
                entry_date=entry_date,
                user_id=current_user.id,
            )
            db.session.add(note)
            db.session.commit()

            flash("Note created successfully!", "success")

            # Redirect based on type
            if note_type == Note.TYPE_JOURNAL:
                return redirect(url_for("notes.journal"))
            elif note_type == Note.TYPE_WEEKLY:
                return redirect(url_for("notes.weekly"))
            return redirect(url_for("notes.list_notes"))

        except ValidationError as e:
            flash(str(e), "error")

    # Pre-fill type from query param
    preset_type = request.args.get("type", Note.TYPE_JOURNAL)
    preset_date = request.args.get("date", "")
    categories = NoteCategory.query.filter_by(user_id=current_user.id).all()

    return render_template(
        "notes/form.html",
        note=None,
        action="Create",
        categories=categories,
        note_types=Note.TYPES,
        preset_type=preset_type,
        preset_date=preset_date,
        prompts=DAILY_PROMPTS if preset_type == Note.TYPE_JOURNAL else [],
    )


@notes_bp.route("/<int:note_id>/edit", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    """Edit an existing note"""
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        try:
            note.title = validate_title(request.form.get("title"), max_length=200)
            note.content = request.form.get("content", "")
            note.note_type = request.form.get("note_type", note.note_type)
            category_id = request.form.get("category_id")
            note.category_id = int(category_id) if category_id else None

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

            db.session.commit()
            flash("Note updated successfully!", "success")

            # Redirect based on type
            if note.note_type == Note.TYPE_JOURNAL:
                return redirect(url_for("notes.journal"))
            elif note.note_type == Note.TYPE_WEEKLY:
                return redirect(url_for("notes.weekly"))
            return redirect(url_for("notes.list_notes"))

        except ValidationError as e:
            flash(str(e), "error")

    categories = NoteCategory.query.filter_by(user_id=current_user.id).all()
    prompts = DAILY_PROMPTS if note.note_type == Note.TYPE_JOURNAL else []

    return render_template(
        "notes/form.html",
        note=note,
        action="Edit",
        categories=categories,
        note_types=Note.TYPES,
        preset_type=note.note_type,
        preset_date=note.entry_date.isoformat() if note.entry_date else "",
        prompts=prompts,
    )


@notes_bp.route("/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    """Delete a note"""
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    note_type = note.note_type
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted successfully!", "success")

    if note_type == Note.TYPE_JOURNAL:
        return redirect(url_for("notes.journal"))
    elif note_type == Note.TYPE_WEEKLY:
        return redirect(url_for("notes.weekly"))
    return redirect(url_for("notes.list_notes"))


@notes_bp.route("/<int:note_id>/toggle_pin", methods=["POST"])
@login_required
def toggle_pin(note_id):
    """Toggle pinned status"""
    note = Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()
    note.pinned = not note.pinned
    db.session.commit()
    return redirect(request.referrer or url_for("notes.list_notes"))


# ---- Journal View ----
@notes_bp.route("/journal")
@login_required
def journal():
    """Journal view - daily entries"""
    today = date.today()

    # Today's entry
    today_entry = Note.query.filter_by(
        user_id=current_user.id,
        note_type=Note.TYPE_JOURNAL,
        entry_date=today,
    ).first()

    # Past entries grouped by month
    past_entries = (
        Note.query.filter_by(user_id=current_user.id, note_type=Note.TYPE_JOURNAL)
        .filter(Note.entry_date < today)
        .order_by(Note.entry_date.desc())
        .all()
    )

    return render_template(
        "notes/journal.html",
        today=today,
        today_entry=today_entry,
        past_entries=past_entries,
        prompts=DAILY_PROMPTS,
    )


# ---- Weekly Reflection View ----
@notes_bp.route("/weekly")
@login_required
def weekly():
    """Weekly reflection view"""
    today = date.today()
    this_week_start = get_week_start(today)

    # This week's reflection
    this_week_entry = Note.query.filter_by(
        user_id=current_user.id,
        note_type=Note.TYPE_WEEKLY,
        entry_date=this_week_start,
    ).first()

    # Past weekly entries
    past_weeks = (
        Note.query.filter_by(user_id=current_user.id, note_type=Note.TYPE_WEEKLY)
        .filter(Note.entry_date < this_week_start)
        .order_by(Note.entry_date.desc())
        .all()
    )

    return render_template(
        "notes/weekly.html",
        this_week_start=this_week_start,
        this_week_entry=this_week_entry,
        past_weeks=past_weeks,
        prompts=WEEKLY_PROMPTS,
    )


# ---- Categories Management ----
@notes_bp.route("/categories")
@login_required
def categories():
    """Manage note categories"""
    cats = (
        NoteCategory.query.filter_by(user_id=current_user.id)
        .order_by(NoteCategory.name)
        .all()
    )
    return render_template("notes/categories.html", categories=cats)


@notes_bp.route("/categories/create", methods=["POST"])
@login_required
def create_category():
    """Create a new category"""
    name = request.form.get("name", "").strip()
    if not name:
        flash("Category name is required.", "error")
        return redirect(url_for("notes.categories"))

    if len(name) > 100:
        flash("Category name too long (max 100 chars).", "error")
        return redirect(url_for("notes.categories"))

    cat = NoteCategory(name=name, user_id=current_user.id)
    db.session.add(cat)
    db.session.commit()
    flash("Category created!", "success")
    return redirect(url_for("notes.categories"))


@notes_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
def delete_category(cat_id):
    """Delete a category"""
    cat = NoteCategory.query.filter_by(
        id=cat_id, user_id=current_user.id
    ).first_or_404()

    # Remove category from notes (don't delete notes)
    Note.query.filter_by(category_id=cat_id).update({"category_id": None})
    db.session.delete(cat)
    db.session.commit()
    flash("Category deleted!", "success")
    return redirect(url_for("notes.categories"))
