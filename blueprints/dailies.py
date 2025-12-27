"""
Dailies Blueprint - handles recurring daily tasks
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database import db, Daily
from datetime import datetime
import json
from validation import validate_title, validate_text, validate_frequency, validate_integer, validate_weekdays, ValidationError

dailies_bp = Blueprint('dailies', __name__, url_prefix='/dailies')

WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

@dailies_bp.route('/')
@login_required
def list_dailies():
    """Display all dailies"""
    dailies = Daily.query.filter_by(user_id=current_user.id).order_by(Daily.created_at.desc()).all()
    return render_template('dailies/list.html', dailies=dailies, weekdays=WEEKDAYS)

@dailies_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_daily():
    """Create a new daily"""
    if request.method == 'POST':
        try:
            title = validate_title(request.form.get('title'), max_length=200)
            description = validate_text(request.form.get('description'), max_length=5000)
            frequency = validate_frequency(request.form.get('frequency'))
            frequency_interval = validate_integer(request.form.get('frequency_interval'), min_val=1, max_val=365) or 1
            
            daily = Daily(
                title=title,
                description=description,
                frequency=frequency,
                frequency_interval=frequency_interval,
                user_id=current_user.id
            )
            
            # Handle custom weekdays
            if frequency == 'custom':
                selected_weekdays = validate_weekdays(request.form.getlist('weekdays'), required=True)
                daily.set_weekdays(selected_weekdays)
            
            db.session.add(daily)
            db.session.commit()
            
            flash('Daily created successfully!', 'success')
            return redirect(url_for('dailies.list_dailies'))
        except ValidationError as e:
            flash(str(e), 'error')
            return render_template('dailies/form.html', daily=None, action='Create', weekdays=WEEKDAYS)
    
    return render_template('dailies/form.html', daily=None, action='Create', weekdays=WEEKDAYS)

@dailies_bp.route('/<int:daily_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_daily(daily_id):
    """Edit an existing daily"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        try:
            daily.title = validate_title(request.form.get('title'), max_length=200)
            daily.description = validate_text(request.form.get('description'), max_length=5000)
            daily.frequency = validate_frequency(request.form.get('frequency'))
            daily.frequency_interval = validate_integer(request.form.get('frequency_interval'), min_val=1, max_val=365) or 1
            
            # Handle custom weekdays
            if daily.frequency == 'custom':
                selected_weekdays = validate_weekdays(request.form.getlist('weekdays'), required=True)
                daily.set_weekdays(selected_weekdays)
            else:
                daily.weekdays = None
            
            db.session.commit()
            flash('Daily updated successfully!', 'success')
            return redirect(url_for('dailies.list_dailies'))
        except ValidationError as e:
            flash(str(e), 'error')
            return render_template('dailies/form.html', daily=daily, action='Edit', weekdays=WEEKDAYS)
    
    return render_template('dailies/form.html', daily=daily, action='Edit', weekdays=WEEKDAYS)

@dailies_bp.route('/<int:daily_id>/toggle', methods=['POST'])
@login_required
def toggle_daily(daily_id):
    """Toggle daily completion status"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()
    
    if not daily.should_complete_today():
        frequency_name = daily.frequency.capitalize()
        flash(f'This daily is not available today. It is set to {frequency_name}.', 'warning')
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('dailies.list_dailies'))
    
    daily.toggle_completion()
    db.session.commit()
    next_page = request.args.get('next')
    if next_page:
        return redirect(next_page)
    return redirect(url_for('dailies.list_dailies'))

@dailies_bp.route('/<int:daily_id>/delete', methods=['POST'])
@login_required
def delete_daily(daily_id):
    """Delete a daily"""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()
    db.session.delete(daily)
    db.session.commit()
    flash('Daily deleted successfully!', 'success')
    return redirect(url_for('dailies.list_dailies'))

@dailies_bp.route('/<int:daily_id>/toggle_for_date', methods=['POST'])
@login_required
def toggle_for_date(daily_id):
    """Toggle completion for a specific date (used on Tomorrow). Disabled for daily frequency."""
    daily = Daily.query.filter_by(id=daily_id, user_id=current_user.id).first_or_404()
    target_date_str = request.form.get('target_date')
    next_page = request.args.get('next') or request.form.get('next')
    if not target_date_str:
        flash('No target date provided.', 'error')
        return redirect(next_page or url_for('dailies.list_dailies'))
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid target date.', 'error')
        return redirect(next_page or url_for('dailies.list_dailies'))

    if daily.frequency == 'daily':
        flash('Daily repetition cannot be scratched early.', 'warning')
        return redirect(next_page or url_for('dailies.list_dailies'))

    daily.toggle_completion_on(target_date)
    db.session.commit()

    if next_page:
        return redirect(next_page)
    return redirect(url_for('dailies.list_dailies'))

