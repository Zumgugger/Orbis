"""
Database models and initialization
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date

db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()

class Todo(db.Model):
    """Todo/Task model"""
    __tablename__ = 'todos'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, completed
    priority = db.Column(db.String(20), default='medium')  # low, medium, high
    due_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Todo {self.id}: {self.title}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class Daily(db.Model):
    """Daily recurring task model"""
    __tablename__ = 'dailies'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    streak_count = db.Column(db.Integer, default=0)
    total_completions = db.Column(db.Integer, default=0)
    last_completed_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Daily {self.id}: {self.title}>'
    
    def is_completed_today(self):
        """Check if this daily was completed today"""
        if not self.last_completed_date:
            return False
        return self.last_completed_date == date.today()
    
    def toggle_completion(self):
        """Toggle daily completion and update streak/totals"""
        today = date.today()
        
        if self.is_completed_today():
            # Uncomplete today's daily
            # Reduce streak and total
            self.streak_count = max(0, self.streak_count - 1)
            self.total_completions = max(0, self.total_completions - 1)
            # Set last completed to yesterday if there was a streak, else None
            if self.streak_count > 0:
                from datetime import timedelta
                self.last_completed_date = today - timedelta(days=1)
            else:
                self.last_completed_date = None
        else:
            # Complete today's daily
            self.total_completions += 1
            
            # Calculate streak
            if self.last_completed_date:
                from datetime import timedelta
                yesterday = today - timedelta(days=1)
                if self.last_completed_date == yesterday:
                    # Continuing streak
                    self.streak_count += 1
                else:
                    # Streak broken, start new
                    self.streak_count = 1
            else:
                # First completion
                self.streak_count = 1
            
            self.last_completed_date = today
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'streak_count': self.streak_count,
            'total_completions': self.total_completions,
            'last_completed_date': self.last_completed_date.isoformat() if self.last_completed_date else None,
            'created_at': self.created_at.isoformat(),
            'is_completed_today': self.is_completed_today()
        }

