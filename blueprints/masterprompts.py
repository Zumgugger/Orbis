"""
Masterprompts Blueprint - manage categories, sections, and builder assembly
"""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from extensions import db
from models import MasterCategory, MasterSection
from validation import ValidationError, validate_text, validate_title

masterprompts_bp = Blueprint("masterprompts", __name__, url_prefix="/masterprompts")


# ---------- Helpers ----------


def _builder_list():
    return session.get("master_builder", [])


def _save_builder(ids):
    session["master_builder"] = ids


def _assemble_text(sections):
    """Combine selected sections into a single masterprompt string."""
    parts = []
    for sec in sections:
        parts.append(f"## {sec.title}\n{sec.body}\n")
        parts.append("---")
    return "\n\n".join(parts).strip()


# Minimal build function to satisfy tests expecting masterprompts.build
def build(sections=None):
    """Return combined text from provided sections or session builder.
    Tests reference masterprompts.build; this provides a stable attribute.
    """
    if sections is None:
        ids = _builder_list()
        if not ids:
            return ""
        q = MasterSection.query.filter(
            MasterSection.user_id == current_user.id, MasterSection.id.in_(ids)
        ).order_by(MasterSection.id)
        return _assemble_text(q.all())
    return _assemble_text(sections)


def _reseq_categories(user_id):
    cats = (
        MasterCategory.query.filter_by(user_id=user_id)
        .order_by(MasterCategory.position, MasterCategory.id)
        .all()
    )
    for idx, c in enumerate(cats):
        c.position = idx
    db.session.commit()


def _reseq_sections(category_id, user_id):
    secs = (
        MasterSection.query.filter_by(category_id=category_id, user_id=user_id)
        .order_by(MasterSection.position, MasterSection.id)
        .all()
    )
    for idx, s in enumerate(secs):
        s.position = idx
    db.session.commit()


# ---------- Routes ----------


@masterprompts_bp.route("/")
@login_required
def index():
    categories = (
        MasterCategory.query.filter_by(user_id=current_user.id)
        .order_by(MasterCategory.position, MasterCategory.id)
        .all()
    )
    selected_id = request.args.get("category_id", type=int)
    if not selected_id and categories:
        selected_id = categories[0].id
    if selected_id and not any(c.id == selected_id for c in categories):
        selected_id = categories[0].id if categories else None

    sections = []
    if selected_id:
        sections = (
            MasterSection.query.filter_by(
                category_id=selected_id, user_id=current_user.id
            )
            .order_by(MasterSection.position, MasterSection.id)
            .all()
        )

    builder_ids = _builder_list()
    builder_sections = []
    if builder_ids:
        builder_sections = (
            MasterSection.query.filter(
                MasterSection.user_id == current_user.id,
                MasterSection.id.in_(builder_ids),
            )
            .order_by(MasterSection.id)
            .all()
        )
        order_map = {sid: idx for idx, sid in enumerate(builder_ids)}
        builder_sections.sort(key=lambda s: order_map.get(s.id, 0))

    combined_text = _assemble_text(builder_sections) if builder_sections else ""

    return render_template(
        "masterprompts/index.html",
        categories=categories,
        selected_id=selected_id,
        sections=sections,
        builder_sections=builder_sections,
        combined_text=combined_text,
    )


# ----- Category CRUD -----


@masterprompts_bp.route("/category/create", methods=["POST"])
@login_required
def create_category():
    try:
        name = validate_title(
            request.form.get("name"), field_name="Category name", max_length=200
        )

        max_pos = (
            db.session.query(func.max(MasterCategory.position))
            .filter_by(user_id=current_user.id)
            .scalar()
        )
        next_pos = (max_pos or 0) + 1
        cat = MasterCategory(user_id=current_user.id, name=name, position=next_pos)
        db.session.add(cat)
        db.session.commit()
        return redirect(url_for("masterprompts.index", category_id=cat.id))
    except ValidationError as e:
        flash(str(e), "error")
        return redirect(url_for("masterprompts.index"))


@masterprompts_bp.route("/category/<int:cat_id>/edit", methods=["POST"])
@login_required
def edit_category(cat_id):
    cat = MasterCategory.query.filter_by(
        id=cat_id, user_id=current_user.id
    ).first_or_404()
    try:
        name = validate_title(
            request.form.get("name"), field_name="Category name", max_length=200
        )
        cat.name = name
        db.session.commit()
        return redirect(url_for("masterprompts.index", category_id=cat.id))
    except ValidationError as e:
        flash(str(e), "error")
        return redirect(url_for("masterprompts.index", category_id=cat.id))


@masterprompts_bp.route("/category/<int:cat_id>/delete", methods=["POST"])
@login_required
def delete_category(cat_id):
    cat = MasterCategory.query.filter_by(
        id=cat_id, user_id=current_user.id
    ).first_or_404()
    # Remove builder entries belonging to this category
    builder_ids = _builder_list()
    remove_ids = [s.id for s in cat.sections]
    builder_ids = [sid for sid in builder_ids if sid not in remove_ids]
    _save_builder(builder_ids)

    db.session.delete(cat)
    db.session.commit()
    _reseq_categories(current_user.id)
    return redirect(url_for("masterprompts.index"))


@masterprompts_bp.route("/category/<int:cat_id>/move/<direction>", methods=["POST"])
@login_required
def move_category(cat_id, direction):
    cat = MasterCategory.query.filter_by(
        id=cat_id, user_id=current_user.id
    ).first_or_404()
    cats = (
        MasterCategory.query.filter_by(user_id=current_user.id)
        .order_by(MasterCategory.position, MasterCategory.id)
        .all()
    )
    idx = cats.index(cat)
    if direction == "up" and idx > 0:
        cats[idx].position, cats[idx - 1].position = (
            cats[idx - 1].position,
            cats[idx].position,
        )
    elif direction == "down" and idx < len(cats) - 1:
        cats[idx].position, cats[idx + 1].position = (
            cats[idx + 1].position,
            cats[idx].position,
        )
    db.session.commit()
    _reseq_categories(current_user.id)
    return redirect(url_for("masterprompts.index", category_id=cat.id))


# ----- Section CRUD -----


@masterprompts_bp.route("/category/<int:cat_id>/section/create", methods=["POST"])
@login_required
def create_section(cat_id):
    cat = MasterCategory.query.filter_by(
        id=cat_id, user_id=current_user.id
    ).first_or_404()
    try:
        title = validate_title(
            request.form.get("title"), field_name="Section title", max_length=255
        )
        body = validate_text(
            request.form.get("body"),
            field_name="Section body",
            required=True,
            max_length=50000,
        )

        max_pos = (
            db.session.query(func.max(MasterSection.position))
            .filter_by(category_id=cat.id, user_id=current_user.id)
            .scalar()
        )
        next_pos = (max_pos or 0) + 1
        sec = MasterSection(
            category_id=cat.id,
            user_id=current_user.id,
            title=title,
            body=body,
            position=next_pos,
        )
        db.session.add(sec)
        db.session.commit()
        return redirect(url_for("masterprompts.index", category_id=cat.id))
    except ValidationError as e:
        flash(str(e), "error")
        return redirect(url_for("masterprompts.index", category_id=cat.id))


@masterprompts_bp.route("/section/<int:sec_id>/edit", methods=["POST"])
@login_required
def edit_section(sec_id):
    sec = MasterSection.query.filter_by(
        id=sec_id, user_id=current_user.id
    ).first_or_404()
    try:
        title = validate_title(
            request.form.get("title"), field_name="Section title", max_length=255
        )
        body = validate_text(
            request.form.get("body"),
            field_name="Section body",
            required=True,
            max_length=50000,
        )
        sec.title = title
        sec.body = body
        db.session.commit()
        return redirect(url_for("masterprompts.index", category_id=sec.category_id))
    except ValidationError as e:
        flash(str(e), "error")
        return redirect(url_for("masterprompts.index", category_id=sec.category_id))


@masterprompts_bp.route("/section/<int:sec_id>/delete", methods=["POST"])
@login_required
def delete_section(sec_id):
    sec = MasterSection.query.filter_by(
        id=sec_id, user_id=current_user.id
    ).first_or_404()
    cat_id = sec.category_id
    # Remove from builder
    builder_ids = [sid for sid in _builder_list() if sid != sec.id]
    _save_builder(builder_ids)

    db.session.delete(sec)
    db.session.commit()
    _reseq_sections(cat_id, current_user.id)
    return redirect(url_for("masterprompts.index", category_id=cat_id))


@masterprompts_bp.route("/section/<int:sec_id>/move/<direction>", methods=["POST"])
@login_required
def move_section(sec_id, direction):
    sec = MasterSection.query.filter_by(
        id=sec_id, user_id=current_user.id
    ).first_or_404()
    secs = (
        MasterSection.query.filter_by(
            category_id=sec.category_id, user_id=current_user.id
        )
        .order_by(MasterSection.position, MasterSection.id)
        .all()
    )
    idx = secs.index(sec)
    if direction == "up" and idx > 0:
        secs[idx].position, secs[idx - 1].position = (
            secs[idx - 1].position,
            secs[idx].position,
        )
    elif direction == "down" and idx < len(secs) - 1:
        secs[idx].position, secs[idx + 1].position = (
            secs[idx + 1].position,
            secs[idx].position,
        )
    db.session.commit()
    _reseq_sections(sec.category_id, current_user.id)
    return redirect(url_for("masterprompts.index", category_id=sec.category_id))


# ----- Builder actions -----


@masterprompts_bp.route("/builder/add/<int:sec_id>", methods=["POST"])
@login_required
def builder_add(sec_id):
    sec = MasterSection.query.filter_by(
        id=sec_id, user_id=current_user.id
    ).first_or_404()
    ids = _builder_list()
    if sec.id not in ids:
        ids.append(sec.id)
        _save_builder(ids)
    return redirect(url_for("masterprompts.index", category_id=sec.category_id))


@masterprompts_bp.route("/builder/remove/<int:sec_id>", methods=["POST"])
@login_required
def builder_remove(sec_id):
    ids = [sid for sid in _builder_list() if sid != sec_id]
    _save_builder(ids)
    return redirect(url_for("masterprompts.index"))


@masterprompts_bp.route("/builder/move/<int:sec_id>/<direction>", methods=["POST"])
@login_required
def builder_move(sec_id, direction):
    ids = _builder_list()
    if sec_id not in ids:
        return redirect(url_for("masterprompts.index"))
    idx = ids.index(sec_id)
    if direction == "up" and idx > 0:
        ids[idx], ids[idx - 1] = ids[idx - 1], ids[idx]
    elif direction == "down" and idx < len(ids) - 1:
        ids[idx], ids[idx + 1] = ids[idx + 1], ids[idx]
    _save_builder(ids)
    return redirect(url_for("masterprompts.index"))


@masterprompts_bp.route("/builder/clear", methods=["POST"])
@login_required
def builder_clear():
    _save_builder([])
    return redirect(url_for("masterprompts.index"))
