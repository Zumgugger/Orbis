"""
Shopping Lists Blueprint
Manage multiple shopping lists with text-based items
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from database import ShoppingList, db
from validation import ValidationError, validate_text, validate_title

shopping_bp = Blueprint("shopping", __name__, url_prefix="/shopping")


@shopping_bp.route("/")
@login_required
def list():
    """Display all shopping lists"""
    lists = (
        ShoppingList.query.filter_by(user_id=current_user.id)
        .order_by(ShoppingList.updated_at.desc())
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

            db.session.commit()
            flash("Shopping list updated!", "success")
            return redirect(url_for("shopping.list"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("shopping/form.html", shopping_list=shopping_list)

    return render_template("shopping/form.html", shopping_list=shopping_list)


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
