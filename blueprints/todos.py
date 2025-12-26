"""
Todos Blueprint - handles all todo/task related routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database import db, Todo
from datetime import datetime, date, timedelta
import requests

todos_bp = Blueprint('todos', __name__)

@todos_bp.route('/')
@login_required
def list_todos():
    """Display all todos"""
    todos = Todo.query.filter_by(user_id=current_user.id).order_by(Todo.created_at.desc()).all()
    pending = [t for t in todos if t.status == 'pending']
    completed = [t for t in todos if t.status == 'completed']
    return render_template('todos/list.html', pending=pending, completed=completed)

@todos_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_todo():
    """Create a new todo"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date')
        
        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('todos.create_todo'))
        
        due_date = None
        if due_date_str:
            try:
                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass
        
        todo = Todo(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            user_id=current_user.id
        )
        db.session.add(todo)
        db.session.commit()
        
        flash('Todo created successfully!', 'success')
        return redirect(url_for('todos.list_todos'))

    return render_template('todos/form.html', todo=None, action='Create', show_due_date=True, preset_due_date='')


@todos_bp.route('/create/today', methods=['GET', 'POST'])
@login_required
def create_todo_today():
    """Create a new todo due today without showing date picker"""
    preset_date = date.today()
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority', 'medium')

        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('todos.create_todo_today'))

        todo = Todo(
            title=title,
            description=description,
            priority=priority,
            due_date=preset_date,
            user_id=current_user.id
        )
        db.session.add(todo)
        db.session.commit()

        flash('Todo for today created!', 'success')
        return redirect(url_for('todos.list_todos'))

    return render_template('todos/form.html', todo=None, action='Create', show_due_date=False, preset_due_date=preset_date.isoformat())


@todos_bp.route('/create/tomorrow', methods=['GET', 'POST'])
@login_required
def create_todo_tomorrow():
    """Create a new todo due tomorrow without showing date picker"""
    preset_date = date.today() + timedelta(days=1)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        priority = request.form.get('priority', 'medium')

        if not title:
            flash('Title is required!', 'error')
            return redirect(url_for('todos.create_todo_tomorrow'))

        todo = Todo(
            title=title,
            description=description,
            priority=priority,
            due_date=preset_date,
            user_id=current_user.id
        )
        db.session.add(todo)
        db.session.commit()

        flash('Todo for tomorrow created!', 'success')
        return redirect(url_for('todos.list_todos'))

    return render_template('todos/form.html', todo=None, action='Create', show_due_date=False, preset_due_date=preset_date.isoformat())

@todos_bp.route('/<int:todo_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_todo(todo_id):
    """Edit an existing todo"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        todo.title = request.form.get('title')
        todo.description = request.form.get('description')
        todo.priority = request.form.get('priority', 'medium')
        due_date_str = request.form.get('due_date')
        
        if due_date_str:
            try:
                todo.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            except ValueError:
                todo.due_date = None
        else:
            todo.due_date = None
        
        db.session.commit()
        flash('Todo updated successfully!', 'success')
        return redirect(url_for('todos.list_todos'))
    
    return render_template('todos/form.html', todo=todo, action='Edit')

@todos_bp.route('/<int:todo_id>/toggle', methods=['POST'])
@login_required
def toggle_todo(todo_id):
    """Toggle todo completion status"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    
    if todo.status == 'pending':
        todo.status = 'completed'
        todo.completed_at = datetime.utcnow()
    else:
        todo.status = 'pending'
        todo.completed_at = None
    
    db.session.commit()
    next_page = request.args.get('next')
    if next_page:
        return redirect(next_page)
    return redirect(url_for('todos.list_todos'))

@todos_bp.route('/<int:todo_id>/delete', methods=['POST'])
@login_required
def delete_todo(todo_id):
    """Delete a todo"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    db.session.delete(todo)
    db.session.commit()
    flash('Todo deleted successfully!', 'success')
    return redirect(url_for('todos.list_todos'))


@todos_bp.route('/<int:todo_id>/due/today', methods=['POST'])
@login_required
def set_due_today(todo_id):
    """Set todo due date to today"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    todo.due_date = date.today()
    db.session.commit()
    return redirect(url_for('todos.list_todos'))


@todos_bp.route('/<int:todo_id>/due/tomorrow', methods=['POST'])
@login_required
def set_due_tomorrow(todo_id):
    """Set todo due date to tomorrow"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    todo.due_date = date.today() + timedelta(days=1)
    db.session.commit()
    return redirect(url_for('todos.list_todos'))

@todos_bp.route('/<int:todo_id>/schedule', methods=['POST'])
@login_required
def schedule_todo(todo_id):
    """Schedule a todo as a Google Calendar event"""
    todo = Todo.query.filter_by(id=todo_id, user_id=current_user.id).first_or_404()
    
    event_date_str = request.form.get('event_date')
    event_time_str = request.form.get('event_time')
    
    if not event_date_str:
        flash('Date is required to schedule.', 'error')
        return redirect(url_for('todos.list_todos'))
    
    try:
        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('todos.list_todos'))
    
    # Build event start/end time
    if event_time_str:
        try:
            start_time = datetime.strptime(event_time_str, '%H:%M').time()
            start_dt = datetime.combine(event_date, start_time)
            # Default 1 hour duration
            end_dt = start_dt.replace(hour=(start_dt.hour + 1) % 24)
        except ValueError:
            flash('Invalid time format.', 'error')
            return redirect(url_for('todos.list_todos'))
    else:
        # All-day event
        start_dt = datetime.combine(event_date, datetime.min.time())
        end_dt = datetime.combine(event_date + timedelta(days=1), datetime.min.time())
    
    # Call Google Calendar API
    try:
        token = current_user.get_oauth_token()
        if not token:
            flash('You must authenticate with Google first.', 'error')
            return redirect(url_for('auth.login'))
        
        event = {
            'summary': todo.title,
            'description': todo.description or '',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC'
            }
        }
        
        headers = {'Authorization': f'Bearer {token}'}
        response = requests.post(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            json=event,
            headers=headers
        )
        
        if response.status_code == 200:
            flash('Todo scheduled in Google Calendar!', 'success')
        else:
            flash(f'Failed to schedule: {response.text}', 'error')
    except Exception as e:
        flash(f'Error scheduling event: {str(e)}', 'error')
    
    return redirect(url_for('todos.list_todos'))
