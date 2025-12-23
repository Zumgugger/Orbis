"""
Orbis - Habit and Task Management System
Main application entry point
"""
from flask import Flask, render_template, redirect, url_for
from database import init_db, db, Todo, Daily
from datetime import datetime, date

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orbis.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    init_db(app)
    
    # Register blueprints
    from blueprints.todos import todos_bp
    from blueprints.dailies import dailies_bp
    from blueprints.habits import habits_bp
    from blueprints.goals import bp as goals_bp
    from blueprints.shopping import bp as shopping_bp
    app.register_blueprint(todos_bp, url_prefix='/todos')
    app.register_blueprint(dailies_bp, url_prefix='/dailies')
    app.register_blueprint(habits_bp, url_prefix='/habits')
    app.register_blueprint(goals_bp, url_prefix='/goals')
    app.register_blueprint(shopping_bp, url_prefix='/shopping')
    
    @app.route('/')
    def index():
        # Get todos due today (all, including completed)
        today = date.today()
        todos_today = Todo.query.filter(
            Todo.due_date == today
        ).all()
        
        # Get all dailies that should be done today OR were completed today (including completed ones)
        dailies_today = []
        all_dailies = Daily.query.all()
        
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
