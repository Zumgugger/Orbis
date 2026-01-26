"""
Shopping Lists Blueprint - manage multiple shopping lists with text-based items
"""
from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import ShoppingList, sync_entity_tags
from validation import ValidationError, validate_text, validate_title


def _parse_tag_ids(form_value: str) -> list[int]:
    """Parse comma-separated tag IDs from form input."""
    if not form_value:
        return []
    return [int(tid) for tid in form_value.split(",") if tid.strip().isdigit()]


shopping_bp = Blueprint("shopping", __name__, url_prefix="/shopping")


@shopping_bp.route("/")
@login_required
def list():
    """Display all shopping lists"""
    lists = (
        ShoppingList.query.filter_by(user_id=current_user.id)
        .order_by(ShoppingList.position.asc(), ShoppingList.updated_at.desc())
        .all()
    )
    return render_template("shopping/list.html", lists=lists)


@shopping_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new shopping list"""
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            items = validate_text(request.form.get("items"), max_length=10000)

            shopping_list = ShoppingList(
                title=title, items=items, user_id=current_user.id
            )
            db.session.add(shopping_list)
            db.session.flush()  # Get shopping_list.id for tag syncing

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            sync_entity_tags(current_user.id, "shopping", shopping_list.id, tag_ids)

            db.session.commit()

            flash("Shopping list created!", "success")
            return redirect(url_for("shopping.list"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("shopping/form.html", shopping_list=None)

    return render_template("shopping/form.html", shopping_list=None)


@shopping_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    """Edit a shopping list"""
    shopping_list = ShoppingList.query.filter_by(
        id=id, user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        try:
            shopping_list.title = validate_title(
                request.form.get("title"), max_length=200
            )
            shopping_list.items = validate_text(
                request.form.get("items"), max_length=10000
            )

            # Sync tags
            tag_ids = _parse_tag_ids(request.form.get("tag_ids", ""))
            sync_entity_tags(current_user.id, "shopping", shopping_list.id, tag_ids)

            db.session.commit()
            flash("Shopping list updated!", "success")
            return redirect(url_for("shopping.list"))
        except ValidationError as e:
            flash(str(e), "error")
            # Get tags for re-rendering form
            from models import get_tags_for_entity

            entity_tags = get_tags_for_entity(
                current_user.id, "shopping", shopping_list.id
            )
            return render_template(
                "shopping/form.html",
                shopping_list=shopping_list,
                entity_tags=entity_tags,
            )

    # Get shopping list's tags
    from models import get_tags_for_entity

    entity_tags = get_tags_for_entity(current_user.id, "shopping", shopping_list.id)
    return render_template(
        "shopping/form.html", shopping_list=shopping_list, entity_tags=entity_tags
    )


@shopping_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    """Delete a shopping list"""
    shopping_list = ShoppingList.query.filter_by(
        id=id, user_id=current_user.id
    ).first_or_404()
    db.session.delete(shopping_list)
    db.session.commit()
    flash("Shopping list deleted!", "success")
    return redirect(url_for("shopping.list"))


@shopping_bp.route("/reorder", methods=["POST"])
@login_required
def reorder():
    """Persist drag-and-drop order of shopping lists for the current user"""
    payload = request.get_json(silent=True) or {}
    order = payload.get("order", [])
    if not isinstance(order, list):
        return {"success": False, "error": "Invalid order payload"}, 400

    try:
        for position, list_id in enumerate(order):
            sl = ShoppingList.query.filter_by(
                id=list_id, user_id=current_user.id
            ).first()
            if sl:
                sl.position = position
        db.session.commit()
        return {"success": True}, 200
    except Exception:
        db.session.rollback()
        return {"success": False, "error": "Failed to persist order"}, 500


@shopping_bp.route("/<int:id>/autosave", methods=["POST"])
@login_required
def autosave(id):
    """Autosave shopping list items via AJAX"""
    shopping_list = ShoppingList.query.filter_by(
        id=id, user_id=current_user.id
    ).first_or_404()

    data = request.get_json(silent=True) or {}
    items = data.get("items")

    if items is not None:
        try:
            items = validate_text(items, max_length=10000)
            shopping_list.items = items
            db.session.commit()
            return jsonify({"success": True, "message": "Saved"})
        except ValidationError as e:
            return jsonify({"success": False, "error": str(e)}), 400

    return jsonify({"success": False, "error": "No items provided"}), 400
