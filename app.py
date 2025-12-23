"""
Orbis - Habit and Task Management System
Main application entry point
"""
from flask import Flask, render_template, redirect, url_for
from database import init_db

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
    app.register_blueprint(todos_bp, url_prefix='/todos')
    app.register_blueprint(dailies_bp, url_prefix='/dailies')
    
    @app.route('/')
    def index():
        return redirect(url_for('todos.list_todos'))
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
