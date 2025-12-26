"""
Orbis - Habit and Task Management System
Main application entry point
"""
from flask import Flask, render_template, redirect, url_for, session
from flask_login import LoginManager, login_required, current_user
from database import init_db, db, Todo, Daily, User, RolloverState, MasterCategory, MasterSection, Habit
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from markupsafe import Markup
from markdown import markdown as md_to_html
import os

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orbis.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Markdown filter for rendering section bodies
    app.jinja_env.filters['markdown'] = lambda text: Markup(md_to_html(text or '', extensions=['extra']))
    
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
    
    app.register_blueprint(todos_bp, url_prefix='/todos')
    app.register_blueprint(dailies_bp, url_prefix='/dailies')
    app.register_blueprint(habits_bp, url_prefix='/habits')
    app.register_blueprint(goals_bp, url_prefix='/goals')
    app.register_blueprint(shopping_bp, url_prefix='/shopping')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(masterprompts_bp, url_prefix='/masterprompts')

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
        today = date.today()
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
        
        return render_template('index.html', 
                             todos=todos_today, 
                             dailies=dailies_today,
                     focused_habits=focused_habits,
                     target_date=target_date,
                     everything_done=everything_done)

    @app.route('/tomorrow')
    @login_required
    def tomorrow():
        process_rollover_for_user(current_user)

        today = date.today()
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

        return render_template(
            'tomorrow.html',
            todos=todos_tomorrow,
            dailies=dailies_tomorrow,
            carryover_ids=carryover_ids,
            focused_habits=focused_habits,
            target_date=target_date
        )
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
