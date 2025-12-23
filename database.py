"""
Database models and initialization
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import json

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
    
    # Frequency fields
    frequency = db.Column(db.String(20), default='daily')  # daily, weekly, monthly, custom
    frequency_interval = db.Column(db.Integer, default=1)  # For daily/weekly/monthly: repeat every N units
    weekdays = db.Column(db.Text, nullable=True)  # JSON: ["monday", "wednesday", "friday"]
    
    def __repr__(self):
        return f'<Daily {self.id}: {self.title}>'
    
    def get_weekdays(self):
        """Get list of weekdays for this daily (if frequency is custom)"""
        if not self.weekdays:
            return []
        try:
            return json.loads(self.weekdays)
        except:
            return []
    
    def set_weekdays(self, weekdays_list):
        """Set weekdays for this daily"""
        self.weekdays = json.dumps(weekdays_list)
    
    def should_complete_today(self):
        """Check if this daily should be completable today based on frequency"""
        today = date.today()
        weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        today_weekday = weekday_names[today.weekday()]
        
        if self.frequency == 'daily':
            # Every N days
            if not self.last_completed_date:
                return True
            days_since_last = (today - self.last_completed_date).days
            return days_since_last >= self.frequency_interval
        elif self.frequency == 'weekly':
            # Every N weeks
            if not self.last_completed_date:
                return True
            days_since_last = (today - self.last_completed_date).days
            return days_since_last >= (7 * self.frequency_interval)
        elif self.frequency == 'monthly':
            # Every N months (approximated as 30 days per month)
            if not self.last_completed_date:
                return True
            days_since_last = (today - self.last_completed_date).days
            return days_since_last >= (30 * self.frequency_interval)
        elif self.frequency == 'custom':
            # Check if today is in the selected weekdays
            return today_weekday in self.get_weekdays()
        
        return True
    
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
            # Set last completed to previous completion date if there was a streak, else None
            if self.streak_count > 0:
                self.last_completed_date = today - timedelta(days=1)
            else:
                self.last_completed_date = None
        else:
            # Complete today's daily
            self.total_completions += 1
            
            # Calculate streak based on frequency
            if self.frequency == 'daily':
                if self.last_completed_date:
                    # Check if last completion was exactly (frequency_interval - 1) days ago
                    days_since = (today - self.last_completed_date).days
                    if days_since == self.frequency_interval:
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
                    self.streak_count = 1
            elif self.frequency == 'weekly':
                if self.last_completed_date:
                    days_since = (today - self.last_completed_date).days
                    week_interval = 7 * self.frequency_interval
                    if days_since >= week_interval and days_since < (week_interval + 7):
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
                    self.streak_count = 1
            elif self.frequency == 'monthly':
                if self.last_completed_date:
                    days_since = (today - self.last_completed_date).days
                    month_interval = 30 * self.frequency_interval
                    if days_since >= month_interval and days_since < (month_interval + 30):
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
                    self.streak_count = 1
            elif self.frequency == 'custom':
                # For custom, streak works like daily within selected days
                if self.last_completed_date:
                    days_since = (today - self.last_completed_date).days
                    if days_since == 1:
                        self.streak_count += 1
                    else:
                        self.streak_count = 1
                else:
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
            'is_completed_today': self.is_completed_today(),
            'frequency': self.frequency,
            'weekdays': self.get_weekdays()
        }


