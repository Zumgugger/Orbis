"""
Admin Blueprint
User management for admins
"""
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from database import db, User
from functools import wraps
from datetime import datetime
from validation import validate_title, validate_email, ValidationError

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

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

@admin_bp.route('/users')
@admin_required
def users():
    """List all users"""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)

@admin_bp.route('/users/<int:user_id>/toggle_role', methods=['POST'])
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

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create a new user"""
    if request.method == 'POST':
        try:
            name = validate_title(request.form.get('name'), field_name="Name", max_length=255)
            email = validate_email(request.form.get('email'))
            role = request.form.get('role', 'user')
            
            if role not in ['user', 'admin']:
                flash('Invalid role selected.', 'error')
                return render_template('admin/create_user.html')
            
            # Check if user already exists
            existing = User.query.filter_by(email=email).first()
            if existing:
                flash(f'User with email {email} already exists.', 'error')
                return render_template('admin/create_user.html')
            
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
        except ValidationError as e:
            flash(str(e), 'error')
            return render_template('admin/create_user.html')
    
    return render_template('admin/create_user.html')

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
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
