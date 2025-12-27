"""
Goals Blueprint
Handles goal tracking with milestone management
"""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from database import Goal, Milestone, db
from validation import ValidationError, validate_text, validate_title

goals_bp = Blueprint("goals", __name__, url_prefix="/goals")


@goals_bp.route("/")
@login_required
def list():
    """List all goals"""
    goals = (
        Goal.query.options(selectinload(Goal.milestones))
        .filter_by(user_id=current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )
    return render_template("goals/list.html", goals=goals)


@goals_bp.route("/create", methods=["GET", "POST"])
@login_required
def create():
    """Create a new goal"""
    if request.method == "POST":
        try:
            title = validate_title(request.form.get("title"), max_length=200)
            description = validate_text(
                request.form.get("description"), max_length=5000
            )

            goal = Goal(title=title, description=description, user_id=current_user.id)
            db.session.add(goal)
            db.session.commit()

            flash("Goal created successfully!", "success")
            return redirect(url_for("goals.edit", id=goal.id))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("goals/form.html", goal=None)

    return render_template("goals/form.html", goal=None)


@goals_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    """Edit a goal"""
    goal = (
        Goal.query.options(selectinload(Goal.milestones))
        .filter_by(id=id, user_id=current_user.id)
        .first_or_404()
    )

    if request.method == "POST":
        try:
            goal.title = validate_title(request.form.get("title"), max_length=200)
            goal.description = validate_text(
                request.form.get("description"), max_length=5000
            )

            db.session.commit()
            flash("Goal updated successfully!", "success")
            return redirect(url_for("goals.list"))
        except ValidationError as e:
            flash(str(e), "error")
            return render_template("goals/form.html", goal=goal)

    return render_template("goals/form.html", goal=goal)


@goals_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
def delete(id):
    """Delete a goal"""
    goal = Goal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash("Goal deleted successfully!", "success")
    return redirect(url_for("goals.list"))


@goals_bp.route("/<int:id>/add_milestone", methods=["POST"])
@login_required
def add_milestone(id):
    """Add a milestone to a goal"""
    goal = Goal.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    try:
        title = validate_title(
            request.form.get("milestone_title"),
            field_name="Milestone title",
            max_length=200,
        )

        # Get the highest order number and add 1
        max_order = (
            db.session.query(db.func.max(Milestone.order))
            .filter_by(goal_id=id)
            .scalar()
            or -1
        )

        milestone = Milestone(goal_id=id, title=title, order=max_order + 1)
        db.session.add(milestone)
        db.session.commit()

        flash("Milestone added successfully!", "success")
    except ValidationError as e:
        flash(str(e), "error")

    return redirect(url_for("goals.edit", id=id))


@goals_bp.route("/<int:goal_id>/milestone/<int:milestone_id>/toggle", methods=["POST"])
@login_required
def toggle_milestone(goal_id, milestone_id):
    """Toggle milestone completion status"""
    milestone = (
        Milestone.query.join(Goal, Milestone.goal_id == Goal.id)
        .filter(
            Milestone.id == milestone_id,
            Goal.id == goal_id,
            Goal.user_id == current_user.id,
        )
        .first_or_404()
    )

    milestone.toggle_completion()
    milestone.goal.update_status()
    db.session.commit()

    return redirect(url_for("goals.list"))


@goals_bp.route("/<int:goal_id>/milestone/<int:milestone_id>/delete", methods=["POST"])
@login_required
def delete_milestone(goal_id, milestone_id):
    """Delete a milestone"""
    milestone = (
        Milestone.query.join(Goal, Milestone.goal_id == Goal.id)
        .filter(
            Milestone.id == milestone_id,
            Goal.id == goal_id,
            Goal.user_id == current_user.id,
        )
        .first_or_404()
    )

    goal = milestone.goal
    db.session.delete(milestone)
    db.session.commit()

    goal.update_status()
    db.session.commit()

    flash("Milestone deleted successfully!", "success")
    return redirect(url_for("goals.edit", id=goal_id))
