"""
Todos Blueprint - handles all todo/task related routes
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from database import db, Todo
from datetime import datetime, date, timedelta
import requests
import os
from time_utils import today_local, tomorrow_local, now_local, get_local_tz

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
    preset_date = today_local()
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
        return redirect(url_for('index'))

    return render_template('todos/form.html', todo=None, action='Create', show_due_date=False, preset_due_date=preset_date.isoformat())


@todos_bp.route('/create/tomorrow', methods=['GET', 'POST'])
@login_required
def create_todo_tomorrow():
    """Create a new todo due tomorrow without showing date picker"""
    preset_date = tomorrow_local()
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
        return redirect(url_for('tomorrow'))

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
    duration_hours_str = request.form.get('duration_hours') or '1'
    duration_minutes_str = request.form.get('duration_minutes') or '0'
    
    if not event_date_str:
        flash('Date is required to schedule.', 'error')
        return redirect(url_for('todos.list_todos'))
    
    try:
        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Invalid date format.', 'error')
        return redirect(url_for('todos.list_todos'))
    
    # Warn if scheduling in the past
    if event_date < today_local():
        flash('Warning: You are scheduling an event in the past.', 'warning')
    elif event_date == today_local() and event_time_str:
        try:
            event_time_obj = datetime.strptime(event_time_str, '%H:%M').time()
            now = now_local()
            if datetime.combine(event_date, event_time_obj, tzinfo=now.tzinfo) < now:
                flash('Warning: You are scheduling an event in the past.', 'warning')
        except ValueError:
            pass
    
    # Build event start/end time
    if event_time_str:
        try:
            start_time = datetime.strptime(event_time_str, '%H:%M').time()
            tzinfo = get_local_tz()
            start_dt = datetime.combine(event_date, start_time, tzinfo=tzinfo)
            # Duration from form (defaults to 1 hour)
            try:
                dh = max(0, int(duration_hours_str))
            except Exception:
                dh = 1
            try:
                dm = max(0, int(duration_minutes_str))
            except Exception:
                dm = 0
            if dh == 0 and dm == 0:
                dm = 45
            end_dt = start_dt + timedelta(hours=dh, minutes=dm)
        except ValueError:
            flash('Invalid time format.', 'error')
            return redirect(url_for('todos.list_todos'))
    else:
        # All-day event
        start_dt = None
        end_dt = None
    
    # Call Google Calendar API
    try:
        from blueprints.auth import get_google_token_for_user
        token = get_google_token_for_user(current_user)
        if not token:
            flash('You must authenticate with Google first.', 'error')
            return redirect(url_for('auth.login'))

        tz = os.getenv('DEFAULT_TIMEZONE', 'Europe/Zurich')
        title = (str(todo.title).strip() if todo.title else '').strip()
        if not title:
            title = f'Todo #{todo.id}'
        event = {
            'summary': title,
            'description': (todo.description or '')
        }
        if start_dt and end_dt:
            event['start'] = {'dateTime': start_dt.isoformat(), 'timeZone': tz}
            event['end'] = {'dateTime': end_dt.isoformat(), 'timeZone': tz}
        else:
            event['start'] = {'date': event_date.isoformat()}
            event['end'] = {'date': (event_date + timedelta(days=1)).isoformat()}

        # Use Authlib client to handle token/refresh
        from blueprints.auth import oauth
        # Debug: log outgoing event structure
        try:
            from flask import current_app
            current_app.logger.info(f'Creating calendar event for todo {todo.id}: {event}')
        except Exception:
            pass

        response = oauth.google.post(
            'https://www.googleapis.com/calendar/v3/calendars/primary/events',
            json=event,
            token=token
        )
        
        if response.status_code in (200, 201):
            flash('Todo scheduled in Google Calendar!', 'success')
        else:
            try:
                err = response.json()
            except Exception:
                err = response.text
            flash(f'Failed to schedule: {err}', 'error')
    except Exception as e:
        flash(f'Error scheduling event: {str(e)}', 'error')
    
    return redirect(url_for('todos.list_todos'))
