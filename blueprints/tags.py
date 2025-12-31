"""
Tags Blueprint - handles tag management and tag-based views
"""
from collections import defaultdict

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import (
    TAG_COLORS,
    Daily,
    EntityTag,
    Goal,
    Habit,
    Idea,
    Note,
    ShoppingList,
    Tag,
    Todo,
    get_tags_for_entity,
    sync_entity_tags,
)
from validation import ValidationError, validate_title

tags_bp = Blueprint("tags", __name__, url_prefix="/tags")

# Entity type to model mapping
ENTITY_MODELS = {
    "todo": Todo,
    "idea": Idea,
    "goal": Goal,
    "daily": Daily,
    "habit": Habit,
    "note": Note,
    "shopping": ShoppingList,
}


@tags_bp.route("/")
@login_required
def list_tags():
    """Display all tags with usage statistics"""
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name.asc()).all()

    # Calculate usage stats
    tag_stats = []
    for tag in tags:
        usage = tag.get_usage_by_type()
        total = sum(usage.values())
        tag_stats.append({"tag": tag, "total": total, "usage": usage})

    # Sort by usage
    tag_stats.sort(key=lambda x: x["total"], reverse=True)

    return render_template("tags/list.html", tag_stats=tag_stats, colors=TAG_COLORS)


@tags_bp.route("/dashboard")
@login_required
def dashboard():
    """Tag dashboard with statistics and entity views"""
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name.asc()).all()

    # Overall statistics
    total_tags = len(tags)
    total_tagged = (
        EntityTag.query.join(Tag).filter(Tag.user_id == current_user.id).count()
    )

    # Usage by entity type
    type_counts = defaultdict(int)
    for tag in tags:
        for et in tag.entity_tags:
            type_counts[et.entity_type] += 1

    # Most used tags (top 10)
    tag_usage = [(tag, tag.get_usage_count()) for tag in tags]
    tag_usage.sort(key=lambda x: x[1], reverse=True)
    top_tags = tag_usage[:10]

    # Recently tagged items
    recent_entity_tags = (
        EntityTag.query.join(Tag)
        .filter(Tag.user_id == current_user.id)
        .order_by(EntityTag.created_at.desc())
        .limit(20)
        .all()
    )

    # Get entity details for recent tags
    recent_items = []
    for et in recent_entity_tags:
        model = ENTITY_MODELS.get(et.entity_type)
        if model:
            entity = model.query.filter_by(
                id=et.entity_id, user_id=current_user.id
            ).first()
            if entity:
                recent_items.append(
                    {
                        "tag": et.tag,
                        "entity_type": et.entity_type,
                        "entity": entity,
                        "created_at": et.created_at,
                    }
                )

    return render_template(
        "tags/dashboard.html",
        tags=tags,
        total_tags=total_tags,
        total_tagged=total_tagged,
        type_counts=dict(type_counts),
        top_tags=top_tags,
        recent_items=recent_items[:15],
        colors=TAG_COLORS,
    )


@tags_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_tag():
    """Create a new tag"""
    if request.method == "POST":
        try:
            name = validate_title(request.form.get("name"), max_length=50)
            color = request.form.get("color", "#6366f1")

            # Check for duplicate
            existing = Tag.query.filter_by(user_id=current_user.id, name=name).first()
            if existing:
                flash(f"Tag '{name}' already exists", "error")
                return render_template(
                    "tags/form.html", tag=None, action="Create", colors=TAG_COLORS
                )

            tag = Tag(user_id=current_user.id, name=name, color=color)
            db.session.add(tag)
            db.session.commit()

            flash(f"Tag '{name}' created successfully!", "success")
            return redirect(url_for("tags.list_tags"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template(
                "tags/form.html", tag=None, action="Create", colors=TAG_COLORS
            )

    return render_template(
        "tags/form.html", tag=None, action="Create", colors=TAG_COLORS
    )


@tags_bp.route("/<int:tag_id>/edit", methods=["GET", "POST"])
@login_required
def edit_tag(tag_id):
    """Edit an existing tag"""
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()

    if request.method == "POST":
        try:
            name = validate_title(request.form.get("name"), max_length=50)
            color = request.form.get("color", tag.color)

            # Check for duplicate (excluding current)
            existing = Tag.query.filter(
                Tag.user_id == current_user.id, Tag.name == name, Tag.id != tag_id
            ).first()
            if existing:
                flash(f"Tag '{name}' already exists", "error")
                return render_template(
                    "tags/form.html", tag=tag, action="Edit", colors=TAG_COLORS
                )

            tag.name = name
            tag.color = color
            db.session.commit()

            flash("Tag updated successfully!", "success")
            return redirect(url_for("tags.list_tags"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template(
                "tags/form.html", tag=tag, action="Edit", colors=TAG_COLORS
            )

    return render_template("tags/form.html", tag=tag, action="Edit", colors=TAG_COLORS)


@tags_bp.route("/<int:tag_id>/delete", methods=["POST"])
@login_required
def delete_tag(tag_id):
    """Delete a tag"""
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
    tag_name = tag.name
    db.session.delete(tag)
    db.session.commit()
    flash(f"Tag '{tag_name}' deleted successfully!", "success")
    return redirect(url_for("tags.list_tags"))


@tags_bp.route("/<int:tag_id>/view")
@login_required
def view_tag(tag_id):
    """View all entities with a specific tag"""
    tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()

    # Get all entity tags
    entity_tags = tag.entity_tags.all()

    # Group by entity type and fetch entities
    entities_by_type = defaultdict(list)
    for et in entity_tags:
        model = ENTITY_MODELS.get(et.entity_type)
        if model:
            entity = model.query.filter_by(
                id=et.entity_id, user_id=current_user.id
            ).first()
            if entity:
                entities_by_type[et.entity_type].append(entity)

    return render_template(
        "tags/view.html", tag=tag, entities_by_type=dict(entities_by_type)
    )


# API endpoints for tag management in forms


@tags_bp.route("/api/list")
@login_required
def api_list_tags():
    """API: Get all tags for current user"""
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name.asc()).all()
    return jsonify([tag.to_dict() for tag in tags])


@tags_bp.route("/api/create", methods=["POST"])
@login_required
def api_create_tag():
    """API: Create a new tag via AJAX"""
    data = request.get_json() or {}
    name = data.get("name", "").strip()
    color = data.get("color", "#6366f1")

    if not name:
        return jsonify({"error": "Tag name is required"}), 400

    if len(name) > 50:
        return jsonify({"error": "Tag name must be 50 characters or less"}), 400

    # Check for duplicate
    existing = Tag.query.filter_by(user_id=current_user.id, name=name).first()
    if existing:
        return (
            jsonify(
                {"error": f"Tag '{name}' already exists", "tag": existing.to_dict()}
            ),
            409,
        )

    tag = Tag(user_id=current_user.id, name=name, color=color)
    db.session.add(tag)
    db.session.commit()

    return jsonify(tag.to_dict()), 201


@tags_bp.route("/api/smart-suggestions", methods=["POST"])
@login_required
def api_smart_suggestions():
    """API: Get smart tag suggestions based on text"""
    data = request.get_json() or {}
    text = data.get("text", "")
    existing_tag_names = data.get("existing_tags", [])

    # Get smart suggestions
    suggested_names = Tag.get_smart_tag_suggestions(text, existing_tag_names)

    # Check which suggestions already exist as tags
    suggestions = []
    for name in suggested_names:
        existing_tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
        if existing_tag:
            suggestions.append(
                {"name": name, "tag": existing_tag.to_dict(), "exists": True}
            )
        else:
            # Suggest a color for new tag
            color_idx = hash(name) % len(TAG_COLORS)
            suggestions.append(
                {"name": name, "color": TAG_COLORS[color_idx], "exists": False}
            )

    return jsonify(suggestions)


@tags_bp.route("/api/entity/<entity_type>/<int:entity_id>")
@login_required
def api_get_entity_tags(entity_type, entity_id):
    """API: Get tags for a specific entity"""
    if entity_type not in ENTITY_MODELS:
        return jsonify({"error": "Invalid entity type"}), 400

    tags = get_tags_for_entity(current_user.id, entity_type, entity_id)
    return jsonify([tag.to_dict() for tag in tags])


@tags_bp.route("/api/entity/<entity_type>/<int:entity_id>/sync", methods=["POST"])
@login_required
def api_sync_entity_tags(entity_type, entity_id):
    """API: Sync tags for an entity"""
    if entity_type not in ENTITY_MODELS:
        return jsonify({"error": "Invalid entity type"}), 400

    # Verify entity exists and belongs to user
    model = ENTITY_MODELS[entity_type]
    entity = model.query.filter_by(id=entity_id, user_id=current_user.id).first()
    if not entity:
        return jsonify({"error": "Entity not found"}), 404

    data = request.get_json() or {}
    tag_ids = data.get("tag_ids", [])

    sync_entity_tags(current_user.id, entity_type, entity_id, tag_ids)
    db.session.commit()

    # Return updated tags
    tags = get_tags_for_entity(current_user.id, entity_type, entity_id)
    return jsonify([tag.to_dict() for tag in tags])
