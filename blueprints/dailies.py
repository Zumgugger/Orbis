"""
Dailies Blueprint - handles recurring daily tasks
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from database import db, Daily
import json

dailies_bp = Blueprint('dailies', __name__)

WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']

@dailies_bp.route('/')
def list_dailies():
    """Display all dailies"""
    dailies = Daily.query.order_by(Daily.created_at.desc()).all()
    return render_template('dailies/list.html', dailies=dailies, weekdays=WEEKDAYS)

@dailies_bp.route('/create', methods=['GET', 'POST'])
def create_daily():
    """Create a new daily"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        frequency = request.form.get('frequency', 'daily')
        
        # Get frequency interval (default 1)
        try:
            frequency_interval = max(1, int(request.form.get('frequency_interval', 1)))
        except:
            frequency_interval = 1
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('dailies.create_daily'))
        
        daily = Daily(
            title=title,
            description=description,
            frequency=frequency,
            frequency_interval=frequency_interval
        )
        
        # Handle custom weekdays
        if frequency == 'custom':
            selected_weekdays = request.form.getlist('weekdays')
            if not selected_weekdays:
                flash('Please select at least one weekday for custom frequency!', 'error')
                return render_template('dailies/form.html', daily=None, action='Create', weekdays=WEEKDAYS)
            daily.set_weekdays(selected_weekdays)
        
        db.session.add(daily)
        db.session.commit()
        
        flash('Daily created successfully!', 'success')
        return redirect(url_for('dailies.list_dailies'))
    
    return render_template('dailies/form.html', daily=None, action='Create', weekdays=WEEKDAYS)

@dailies_bp.route('/<int:daily_id>/edit', methods=['GET', 'POST'])
def edit_daily(daily_id):
    """Edit an existing daily"""
    daily = Daily.query.get_or_404(daily_id)
    
    if request.method == 'POST':
        daily.title = request.form.get('title')
        daily.description = request.form.get('description')
        daily.frequency = request.form.get('frequency', 'daily')
        
        # Get frequency interval (default 1)
        try:
            daily.frequency_interval = max(1, int(request.form.get('frequency_interval', 1)))
        except:
            daily.frequency_interval = 1
        
        # Handle custom weekdays
        if daily.frequency == 'custom':
            selected_weekdays = request.form.getlist('weekdays')
            if not selected_weekdays:
                flash('Please select at least one weekday for custom frequency!', 'error')
                return render_template('dailies/form.html', daily=daily, action='Edit', weekdays=WEEKDAYS)
            daily.set_weekdays(selected_weekdays)
        else:
            daily.weekdays = None
        
        db.session.commit()
        flash('Daily updated successfully!', 'success')
        return redirect(url_for('dailies.list_dailies'))
    
    return render_template('dailies/form.html', daily=daily, action='Edit', weekdays=WEEKDAYS)

@dailies_bp.route('/<int:daily_id>/toggle', methods=['POST'])
def toggle_daily(daily_id):
    """Toggle daily completion status"""
    daily = Daily.query.get_or_404(daily_id)
    
    if not daily.should_complete_today():
        frequency_name = daily.frequency.capitalize()
        flash(f'This daily is not available today. It is set to {frequency_name}.', 'warning')
        return redirect(url_for('dailies.list_dailies'))
    
    daily.toggle_completion()
    db.session.commit()
    return redirect(url_for('dailies.list_dailies'))

@dailies_bp.route('/<int:daily_id>/delete', methods=['POST'])
def delete_daily(daily_id):
    """Delete a daily"""
    daily = Daily.query.get_or_404(daily_id)
    db.session.delete(daily)
    db.session.commit()
    flash('Daily deleted successfully!', 'success')
    return redirect(url_for('dailies.list_dailies'))

