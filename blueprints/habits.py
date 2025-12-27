"""
Habits Blueprint - handles habit tracking with +/- counters
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from database import db, Habit
from validation import validate_title, validate_text, validate_difficulty, ValidationError

habits_bp = Blueprint('habits', __name__, url_prefix='/habits')

@habits_bp.route('/')
@login_required
def list_habits():
    """Display all habits"""
    habits = Habit.query.filter_by(user_id=current_user.id).order_by(Habit.position.asc(), Habit.id.asc()).all()
    return render_template('habits/list.html', habits=habits)

@habits_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_habit():
    """Create a new habit"""
    if request.method == 'POST':
        try:
            title = validate_title(request.form.get('title'), max_length=200)
            description = validate_text(request.form.get('description'), max_length=5000)
            difficulty = validate_difficulty(request.form.get('difficulty'))
            
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
        except ValidationError as e:
            flash(str(e), 'error')
            return render_template('habits/form.html', habit=None, action='Create')
    
    return render_template('habits/form.html', habit=None, action='Create')

@habits_bp.route('/<int:habit_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_habit(habit_id):
    """Edit an existing habit"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            habit.title = validate_title(request.form.get('title'), max_length=200)
            habit.description = validate_text(request.form.get('description'), max_length=5000)
            habit.difficulty = validate_difficulty(request.form.get('difficulty'))
            
            db.session.commit()
            flash('Habit updated successfully!', 'success')
            return redirect(url_for('habits.list_habits'))
        except ValidationError as e:
            flash(str(e), 'error')
            return render_template('habits/form.html', habit=habit, action='Edit')
    
    return render_template('habits/form.html', habit=habit, action='Edit')

@habits_bp.route('/<int:habit_id>/increment', methods=['POST'])
@login_required
def increment_habit(habit_id):
    """Increment habit count (+1)"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    target_date = None
    target_date_str = request.form.get('target_date')
    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            target_date = None

    habit.increment(target_date=target_date)
    db.session.commit()
    next_page = request.args.get('next') or request.form.get('next')
    if next_page:
        return redirect(next_page)
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


@habits_bp.route('/reorder', methods=['POST'])
@login_required
def reorder_habits():
    """Persist new habit order from drag-and-drop"""
    try:
        data = request.get_json(silent=True) or {}
        ids = data.get('order', [])
        
        if not isinstance(ids, list):
            return jsonify({'error': 'Invalid payload', 'message': 'Order must be a list'}), 400
        
        # Filter to user's habits only
        user_habits = Habit.query.filter_by(user_id=current_user.id).all()
        user_ids = {h.id for h in user_habits}
        filtered = [hid for hid in ids if hid in user_ids]
        
        for idx, hid in enumerate(filtered):
            Habit.query.filter_by(id=hid, user_id=current_user.id).update({'position': idx})
        
        db.session.commit()
        return jsonify({'status': 'ok'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to reorder', 'message': str(e)}), 500


@habits_bp.route('/<int:habit_id>/focus', methods=['POST'])
@login_required
def toggle_focus(habit_id):
    """Toggle focused flag for habit"""
    habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first_or_404()
    habit.focused = not habit.focused
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
