"""
Habits Blueprint - handles habit tracking with +/- counters
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from database import db, Habit

habits_bp = Blueprint('habits', __name__)

@habits_bp.route('/')
@login_required
def list_habits():
    """Display all habits"""
    habits = Habit.query.filter_by(user_id=current_user.id).order_by(Habit.created_at.desc()).all()
    return render_template('habits/list.html', habits=habits)

@habits_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_habit():
    """Create a new habit"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        difficulty = request.form.get('difficulty', 'normal')
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('habits.create_habit'))
        
        habit = Habit(
            title=title,
            description=description,
            difficulty=difficulty,
            user_id=current_user.id
        )
        db.session.add(habit)
        db.session.commit()
        
        flash('Habit created successfully!', 'success')
        return redirect(url_for('habits.list_habits'))
    
    return render_template('habits/form.html', habit=None, action='Create')

@habits_bp.route('/<int:habit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_habit(habit_id):
    """Edit an existing habit"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        habit.title = request.form.get('title')
        habit.description = request.form.get('description')
        habit.difficulty = request.form.get('difficulty', 'normal')
        
        db.session.commit()
        flash('Habit updated successfully!', 'success')
        return redirect(url_for('habits.list_habits'))
    
    return render_template('habits/form.html', habit=habit, action='Edit')

@habits_bp.route('/<int:habit_id>/increment', methods=['POST'])
@login_required
def increment_habit(habit_id):
    """Increment habit count (+1)"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.increment()
    db.session.commit()
    return redirect(url_for('habits.list_habits'))

@habits_bp.route('/<int:habit_id>/decrement', methods=['POST'])
@login_required
def decrement_habit(habit_id):
    """Decrement habit count (-1)"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.decrement()
    db.session.commit()
    return redirect(url_for('habits.list_habits'))

@habits_bp.route('/<int:habit_id>/cycle_difficulty', methods=['POST'])
@login_required
def cycle_difficulty(habit_id):
    """Cycle through difficulty levels: easy -> normal -> hard -> easy"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    
    if habit.difficulty == 'easy':
        habit.difficulty = 'normal'
    elif habit.difficulty == 'normal':
        habit.difficulty = 'hard'
    else:  # hard
        habit.difficulty = 'easy'
    
    db.session.commit()
    return redirect(url_for('habits.list_habits'))

@habits_bp.route('/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    """Delete a habit"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    db.session.delete(habit)
    db.session.commit()
    flash('Habit deleted successfully!', 'success')
    return redirect(url_for('habits.list_habits'))
