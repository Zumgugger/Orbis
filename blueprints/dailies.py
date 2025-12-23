"""
Dailies Blueprint - handles recurring daily tasks
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from database import db, Daily

dailies_bp = Blueprint('dailies', __name__)

@dailies_bp.route('/')
def list_dailies():
    """Display all dailies"""
    dailies = Daily.query.order_by(Daily.created_at.desc()).all()
    return render_template('dailies/list.html', dailies=dailies)

@dailies_bp.route('/create', methods=['GET', 'POST'])
def create_daily():
    """Create a new daily"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('dailies.create_daily'))
        
        daily = Daily(
            title=title,
            description=description
        )
        db.session.add(daily)
        db.session.commit()
        
        flash('Daily created successfully!', 'success')
        return redirect(url_for('dailies.list_dailies'))
    
    return render_template('dailies/form.html', daily=None, action='Create')

@dailies_bp.route('/<int:daily_id>/edit', methods=['GET', 'POST'])
def edit_daily(daily_id):
    """Edit an existing daily"""
    daily = Daily.query.get_or_404(daily_id)
    
    if request.method == 'POST':
        daily.title = request.form.get('title')
        daily.description = request.form.get('description')
        
        db.session.commit()
        flash('Daily updated successfully!', 'success')
        return redirect(url_for('dailies.list_dailies'))
    
    return render_template('dailies/form.html', daily=daily, action='Edit')

@dailies_bp.route('/<int:daily_id>/toggle', methods=['POST'])
def toggle_daily(daily_id):
    """Toggle daily completion status"""
    daily = Daily.query.get_or_404(daily_id)
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
