"""
Orbis - Habit and Task Management System
Main application entry point
"""
from flask import Flask, render_template, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from database import init_db, db, Todo, Daily, User
from datetime import datetime, date
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orbis.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
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
    
    app.register_blueprint(todos_bp, url_prefix='/todos')
    app.register_blueprint(dailies_bp, url_prefix='/dailies')
    app.register_blueprint(habits_bp, url_prefix='/habits')
    app.register_blueprint(goals_bp, url_prefix='/goals')
    app.register_blueprint(shopping_bp, url_prefix='/shopping')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    @app.route('/')
    @login_required
    def index():
        # Get todos due today for current user (all, including completed)
        today = date.today()
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
        
        # Check if everything is done (no pending items)
        pending_todos = [t for t in todos_today if t.status == 'pending']
        everything_done = len(pending_todos) == 0 and len(dailies_not_done) == 0
        
        return render_template('index.html', 
                             todos=todos_today, 
                             dailies=dailies_today,
                             everything_done=everything_done)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
