"""
Orbis - Habit and Task Management System
Main application entry point
"""
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from flask_login import LoginManager, login_required, current_user
from database import init_db, db, Todo, Daily, User, RolloverState, MasterCategory, MasterSection, Habit
from datetime import datetime, date, timedelta, time
from dotenv import load_dotenv
from markupsafe import Markup
from markdown import markdown as md_to_html
from flask_wtf import CSRFProtect
import os
from time_utils import get_local_tz, today_local, tomorrow_local, iso_start_of_day

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orbis.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # Avoid unexpected expiry during long sessions

    # Markdown filter for rendering section bodies
    app.jinja_env.filters['markdown'] = lambda text: Markup(md_to_html(text or '', extensions=['extra']))
    # CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    # Expose csrf_token to templates
    from flask_wtf.csrf import generate_csrf
    app.jinja_env.globals['csrf_token'] = generate_csrf
    
    # Initialize database
    init_db(app)
    
    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialize OAuth
    from blueprints.auth import init_oauth
    init_oauth(app)
    
    # Register blueprints
    from blueprints.todos import todos_bp
    from blueprints.dailies import dailies_bp
    from blueprints.habits import habits_bp
    from blueprints.goals import bp as goals_bp
    from blueprints.shopping import bp as shopping_bp
    from blueprints.auth import bp as auth_bp
    from blueprints.admin import bp as admin_bp
    from blueprints.masterprompts import bp as masterprompts_bp
    from blueprints.ideas import ideas_bp
    
    app.register_blueprint(todos_bp, url_prefix='/todos')
    app.register_blueprint(dailies_bp, url_prefix='/dailies')
    app.register_blueprint(habits_bp, url_prefix='/habits')
    app.register_blueprint(goals_bp, url_prefix='/goals')
    app.register_blueprint(shopping_bp, url_prefix='/shopping')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(masterprompts_bp, url_prefix='/masterprompts')
    app.register_blueprint(ideas_bp)

    # Error handlers
    @app.errorhandler(400)
    def bad_request(e):
        """Handle 400 Bad Request errors"""
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Bad request', 'message': str(e)}), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden(e):
        """Handle 403 Forbidden errors"""
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 Not Found errors"""
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Not found', 'message': 'Resource not found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        """Handle 500 Internal Server errors"""
        db.session.rollback()  # Rollback any failed transactions
        app.logger.error(f'Server Error: {e}')
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle uncaught exceptions"""
        db.session.rollback()
        app.logger.exception(f'Unhandled exception: {e}')
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500
        return render_template('errors/500.html'), 500

    def fetch_calendar_events(user, start_date, end_date):
        """Fetch primary calendar events between start_date (inclusive) and end_date (exclusive)."""
        from blueprints.auth import oauth, get_google_token_for_user

        token = get_google_token_for_user(user, logger=app.logger)
        if not token:
            return []

        tz = get_local_tz()

        time_min = iso_start_of_day(start_date)
        time_max = iso_start_of_day(end_date)

        try:
            resp = oauth.google.get(
                'https://www.googleapis.com/calendar/v3/calendars/primary/events',
                params={
                    'timeMin': time_min,
                    'timeMax': time_max,
                    'singleEvents': True,
                    'orderBy': 'startTime'
                },
                token=token
            )
        except Exception as exc:
            app.logger.warning(f'Calendar fetch failed: {exc}')
            return []

        if resp.status_code != 200:
            app.logger.warning(f'Calendar fetch returned {resp.status_code}: {resp.text}')
            return []

        events = []
        data = resp.json()
        for item in data.get('items', []):
            start = item.get('start', {})
            end = item.get('end', {})
            is_all_day = 'date' in start
            raw_start = start.get('dateTime') or start.get('date')
            raw_end = end.get('dateTime') or end.get('date')

            def fmt_dt(val):
                if not val:
                    return None
                try:
                    dt = datetime.fromisoformat(val.replace('Z', '+00:00'))
                    if tz:
                        dt = dt.astimezone(tz)
                    return dt
                except Exception:
                    return None

            start_dt = fmt_dt(raw_start) if not is_all_day else None
            end_dt = fmt_dt(raw_end) if not is_all_day else None
            events.append({
                'title': item.get('summary') or '(No title)',
                'start_raw': raw_start,
                'end_raw': raw_end,
                'start_dt': start_dt,
                'end_dt': end_dt,
                'all_day': is_all_day,
                'html_link': item.get('htmlLink')
            })

        return events

    def process_rollover_for_user(user):
        """Shift unfinished items forward once per day and break missed streaks."""
        if not user.is_authenticated:
            return

        today = date.today()
        state = RolloverState.query.filter_by(user_id=user.id).first()

        if not state:
            state = RolloverState(user_id=user.id, last_processed_date=today)
            db.session.add(state)
            db.session.commit()
            return

        current_day = state.last_processed_date

        while current_day < today:
            next_day = current_day + timedelta(days=1)

            # Move pending todos forward by one day
            pending_todos = Todo.query.filter(
                Todo.user_id == user.id,
                Todo.status == 'pending',
                Todo.due_date == current_day
            ).all()
            for todo in pending_todos:
                todo.due_date = next_day

            # Break streak for dailies missed on the day
            user_dailies = Daily.query.filter_by(user_id=user.id).all()
            for daily in user_dailies:
                if daily.should_complete_on(current_day) and not daily.is_completed_on(current_day):
                    daily.streak_count = 0

            db.session.commit()
            current_day = next_day

        state.last_processed_date = today
        db.session.commit()
    
    @app.route('/')
    @login_required
    def index():
        process_rollover_for_user(current_user)
        # Get todos due today for current user (all, including completed)
        today = today_local()
        target_date = today
        todos_today = Todo.query.filter(
            Todo.user_id == current_user.id,
            Todo.due_date == today
        ).all()
        
        # Get all dailies that should be done today OR were completed today (including completed ones)
        dailies_today = []
        all_dailies = Daily.query.filter_by(user_id=current_user.id).all()
        
        for daily in all_dailies:
            # Include if it should be done today OR if it was already completed today
            if daily.should_complete_today() or daily.is_completed_today():
                dailies_today.append(daily)
        
        # Get only the ones not yet completed for the "everything_done" check
        dailies_not_done = [d for d in dailies_today if not d.is_completed_today()]

        focused_habits = Habit.query.filter_by(user_id=current_user.id, focused=True).order_by(Habit.position.asc(), Habit.id.asc()).all()
        focused_not_done = [h for h in focused_habits if h.last_increment_date != today]
        
        # Check if everything is done (no pending items)
        pending_todos = [t for t in todos_today if t.status == 'pending']
        everything_done = len(pending_todos) == 0 and len(dailies_not_done) == 0 and len(focused_not_done) == 0
        
        calendar_today = fetch_calendar_events(current_user, today, today + timedelta(days=1))
        for ev in calendar_today:
            if ev.get('all_day'):
                ev['time_label'] = 'Today · All-day'
            elif ev.get('start_dt'):
                ev['time_label'] = f"Today · {ev['start_dt'].strftime('%H:%M')}"
            else:
                ev['time_label'] = 'Today'

        combined_todos = [{'kind': 'calendar', 'event': ev} for ev in calendar_today]
        combined_todos += [{'kind': 'todo', 'todo': t} for t in todos_today]

        return render_template('index.html', 
                     todos=todos_today, 
                     dailies=dailies_today,
                 focused_habits=focused_habits,
                 target_date=target_date,
                     everything_done=everything_done,
                     combined_todos=combined_todos)

    @app.route('/tomorrow')
    @login_required
    def tomorrow():
        process_rollover_for_user(current_user)

        today = today_local()
        target_date = today + timedelta(days=1)

        todos_tomorrow = Todo.query.filter(
            Todo.user_id == current_user.id,
            Todo.due_date == target_date
        ).all()

        all_dailies = Daily.query.filter_by(user_id=current_user.id).all()
        carryover_ids = set()
        due_ids = set()

        for daily in all_dailies:
            if daily.should_complete_on(today) and not daily.is_completed_on(today):
                carryover_ids.add(daily.id)
            if daily.should_complete_on(target_date):
                due_ids.add(daily.id)

        dailies_tomorrow = [
            daily for daily in all_dailies
            if daily.id in carryover_ids or daily.id in due_ids
        ]

        focused_habits = Habit.query.filter_by(user_id=current_user.id, focused=True).order_by(Habit.position.asc(), Habit.id.asc()).all()

        calendar_tomorrow = fetch_calendar_events(current_user, target_date, target_date + timedelta(days=1))
        for ev in calendar_tomorrow:
            if ev.get('all_day'):
                ev['time_label'] = 'Tomorrow · All-day'
            elif ev.get('start_dt'):
                ev['time_label'] = f"Tomorrow · {ev['start_dt'].strftime('%H:%M')}"
            else:
                ev['time_label'] = 'Tomorrow'

        combined_todos = [{'kind': 'calendar', 'event': ev} for ev in calendar_tomorrow]
        combined_todos += [{'kind': 'todo', 'todo': t} for t in todos_tomorrow]

        return render_template(
            'tomorrow.html',
            todos=todos_tomorrow,
            dailies=dailies_tomorrow,
            carryover_ids=carryover_ids,
            focused_habits=focused_habits,
            target_date=target_date,
            combined_todos=combined_todos
        )
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
