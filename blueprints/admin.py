"""
Admin Blueprint
User management for admins
"""
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from database import db, User
from functools import wraps
from datetime import datetime

bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/users')
@admin_required
def users():
    """List all users"""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)

@bp.route('/users/<int:user_id>/toggle_role', methods=['POST'])
@admin_required
def toggle_role(user_id):
    """Toggle user role between admin and user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent removing your own admin role
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'error')
        return redirect(url_for('admin.users'))
    
    # Toggle role
    if user.role == 'admin':
        user.role = 'user'
        flash(f'{user.email} is now a regular user.', 'success')
    else:
        user.role = 'admin'
        flash(f'{user.email} is now an admin.', 'success')
    
    db.session.commit()
    return redirect(url_for('admin.users'))

@bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create a new user"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role', 'user')
        
        if not name or not email:
            flash('Name and email are required.', 'error')
            return redirect(url_for('admin.create_user'))
        
        # Check if user already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash(f'User with email {email} already exists.', 'error')
            return redirect(url_for('admin.create_user'))
        
        # Create user
        user = User(
            google_id=f'admin_created_{email}',
            email=email,
            name=name,
            role=role,
            created_at=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        flash(f'User {name} ({email}) created successfully as {role}.', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/create_user.html')

@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.users'))
    
    # Store user info for flash message
    user_name = user.name
    user_email = user.email
    
    # Delete user (cascade will delete related data)
    db.session.delete(user)
    db.session.commit()
    
    flash(f'User {user_name} ({user_email}) has been deleted.', 'success')
    return redirect(url_for('admin.users'))
