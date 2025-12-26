"""
Goals Blueprint
Handles goal tracking with milestone management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database import db, Goal, Milestone
from sqlalchemy.orm import selectinload

bp = Blueprint('goals', __name__, url_prefix='/goals')

@bp.route('/')
@login_required
def list():
    """List all goals"""
    goals = (
        Goal.query.options(selectinload(Goal.milestones))
        .filter_by(user_id=current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )
    return render_template('goals/list.html', goals=goals)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new goal"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('goals.create'))
        
        goal = Goal(title=title, description=description, user_id=current_user.id)
        db.session.add(goal)
        db.session.commit()
        
        flash('Goal created successfully!', 'success')
        return redirect(url_for('goals.edit', id=goal.id))
    
    return render_template('goals/form.html', goal=None)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    """Edit a goal"""
    goal = (
        Goal.query.options(selectinload(Goal.milestones))
        .filter_by(id=id, user_id=current_user.id)
        .first_or_404()
    )
    
    if request.method == 'POST':
        goal.title = request.form.get('title')
        goal.description = request.form.get('description')
        
        if not goal.title:
            flash('Title is required!', 'error')
            return redirect(url_for('goals.edit', id=id))
        
        db.session.commit()
        flash('Goal updated successfully!', 'success')
        return redirect(url_for('goals.list'))
    
    return render_template('goals/form.html', goal=goal)

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    """Delete a goal"""
    goal = Goal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    db.session.delete(goal)
    db.session.commit()
    flash('Goal deleted successfully!', 'success')
    return redirect(url_for('goals.list'))

@bp.route('/<int:id>/add_milestone', methods=['POST'])
@login_required
def add_milestone(id):
    """Add a milestone to a goal"""
    goal = Goal.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    title = request.form.get('milestone_title')
    
    if not title:
        flash('Milestone title is required!', 'error')
        return redirect(url_for('goals.edit', id=id))
    
    # Get the highest order number and add 1
    max_order = db.session.query(db.func.max(Milestone.order)).filter_by(goal_id=id).scalar() or -1
    
    milestone = Milestone(
        goal_id=id,
        title=title,
        order=max_order + 1
    )
    db.session.add(milestone)
    db.session.commit()
    
    flash('Milestone added successfully!', 'success')
    return redirect(url_for('goals.edit', id=id))

@bp.route('/<int:goal_id>/milestone/<int:milestone_id>/toggle', methods=['POST'])
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

    return redirect(url_for('goals.list'))

@bp.route('/<int:goal_id>/milestone/<int:milestone_id>/delete', methods=['POST'])
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

    flash('Milestone deleted successfully!', 'success')
    return redirect(url_for('goals.edit', id=goal_id))
