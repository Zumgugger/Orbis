"""
Goals Blueprint
Handles goal tracking with milestone management
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db, Goal, Milestone

bp = Blueprint('goals', __name__, url_prefix='/goals')

@bp.route('/')
def list():
    """List all goals"""
    goals = Goal.query.order_by(Goal.created_at.desc()).all()
    return render_template('goals/list.html', goals=goals)

@bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new goal"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('goals.create'))
        
        goal = Goal(title=title, description=description)
        db.session.add(goal)
        db.session.commit()
        
        flash('Goal created successfully!', 'success')
        return redirect(url_for('goals.edit', id=goal.id))
    
    return render_template('goals/form.html', goal=None)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """Edit a goal"""
    goal = Goal.query.get_or_404(id)
    
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
def delete(id):
    """Delete a goal"""
    goal = Goal.query.get_or_404(id)
    db.session.delete(goal)
    db.session.commit()
    flash('Goal deleted successfully!', 'success')
    return redirect(url_for('goals.list'))

@bp.route('/<int:id>/add_milestone', methods=['POST'])
def add_milestone(id):
    """Add a milestone to a goal"""
    goal = Goal.query.get_or_404(id)
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
def toggle_milestone(goal_id, milestone_id):
    """Toggle milestone completion status"""
    milestone = Milestone.query.get_or_404(milestone_id)
    goal = Goal.query.get_or_404(goal_id)
    
    if milestone.goal_id != goal_id:
        flash('Invalid milestone!', 'error')
        return redirect(url_for('goals.list'))
    
    milestone.toggle_completion()
    goal.update_status()
    db.session.commit()
    
    return redirect(url_for('goals.list'))

@bp.route('/<int:goal_id>/milestone/<int:milestone_id>/delete', methods=['POST'])
def delete_milestone(goal_id, milestone_id):
    """Delete a milestone"""
    milestone = Milestone.query.get_or_404(milestone_id)
    
    if milestone.goal_id != goal_id:
        flash('Invalid milestone!', 'error')
        return redirect(url_for('goals.edit', id=goal_id))
    
    db.session.delete(milestone)
    db.session.commit()
    
    # Update goal status after deleting milestone
    goal = Goal.query.get_or_404(goal_id)
    goal.update_status()
    db.session.commit()
    
    flash('Milestone deleted successfully!', 'success')
    return redirect(url_for('goals.edit', id=goal_id))
