"""
Database models and initialization
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, date, timedelta
import json

db = SQLAlchemy()

def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        _ensure_habit_columns()
        _ensure_user_columns()


def _ensure_habit_columns():
    """Add missing habit columns for ordering, focus, and last increment date (SQLite-safe)."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    columns = {col['name'] for col in insp.get_columns('habits')}
    ddl = []
    if 'position' not in columns:
        ddl.append('ALTER TABLE habits ADD COLUMN position INTEGER DEFAULT 0')
    if 'focused' not in columns:
        ddl.append('ALTER TABLE habits ADD COLUMN focused BOOLEAN DEFAULT 0')
    if 'last_increment_date' not in columns:
        ddl.append('ALTER TABLE habits ADD COLUMN last_increment_date DATE')
    for stmt in ddl:
        db.session.execute(text(stmt))
    if ddl:
        db.session.commit()

def _ensure_user_columns():
    """Add missing user columns for OAuth token (SQLite-safe)."""
    from sqlalchemy import inspect, text
    insp = inspect(db.engine)
    columns = {col['name'] for col in insp.get_columns('users')}
    ddl = []
    if 'oauth_token' not in columns:
        ddl.append('ALTER TABLE users ADD COLUMN oauth_token TEXT')
    for stmt in ddl:
        db.session.execute(text(stmt))
    if ddl:
        db.session.commit()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=True)
    profile_pic = db.Column(db.String(500), nullable=True)
    role = db.Column(db.String(20), default='user')  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    oauth_token = db.Column(db.Text, nullable=True)  # Store OAuth token JSON (access+refresh)
    
    def __repr__(self):
        return f'<User {self.id}: {self.email}>'
    
    def get_oauth_token(self):
        """Retrieve stored OAuth token as dict"""
        if not self.oauth_token:
            return None
        try:
            return json.loads(self.oauth_token)
        except Exception:
            return None
    
    def set_oauth_token(self, token):
        """Store OAuth token (dict or string)"""
        try:
            self.oauth_token = json.dumps(token) if isinstance(token, dict) else token
        except Exception:
            self.oauth_token = token
        db.session.commit()
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'google_id': self.google_id,
            'email': self.email,
            'name': self.name,
            'profile_pic': self.profile_pic,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Todo(db.Model):
    """Todo/Task model"""
    __tablename__ = 'todos'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
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
        return self.should_complete_on(date.today())

    def should_complete_on(self, target_date):
        """Check if this daily should be completable on a specific date"""
        weekday_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        target_weekday = weekday_names[target_date.weekday()]

        if self.last_completed_date and target_date < self.last_completed_date:
            return False

        if self.frequency == 'daily':
            if not self.last_completed_date:
                return True
            days_since_last = (target_date - self.last_completed_date).days
            return days_since_last >= self.frequency_interval
        if self.frequency == 'weekly':
            if not self.last_completed_date:
                return True
            days_since_last = (target_date - self.last_completed_date).days
            return days_since_last >= (7 * self.frequency_interval)
        if self.frequency == 'monthly':
            if not self.last_completed_date:
                return True
            days_since_last = (target_date - self.last_completed_date).days
            return days_since_last >= (30 * self.frequency_interval)
        if self.frequency == 'custom':
            return target_weekday in self.get_weekdays()

        return True

    def is_completed_on(self, target_date):
        """Check if this daily was completed on a specific date"""
        if not self.last_completed_date:
            return False
        return self.last_completed_date == target_date
    
    def is_completed_today(self):
        """Check if this daily was completed today"""
        return self.is_completed_on(date.today())
    
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

    def toggle_completion_on(self, target_date):
        """Toggle completion for a specific date (used for early scratch on Tomorrow)."""
        if not isinstance(target_date, date):
            return

        if self.is_completed_on(target_date):
            # Uncomplete for target date
            self.streak_count = max(0, self.streak_count - 1)
            self.total_completions = max(0, self.total_completions - 1)
            if self.streak_count > 0:
                self.last_completed_date = target_date - timedelta(days=1)
            else:
                self.last_completed_date = None
            return

        # Complete for target date
        self.total_completions += 1

        if self.frequency == 'daily':
            # Streak logic analogous to toggle_completion but using target_date
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                if days_since == self.frequency_interval:
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1
        elif self.frequency == 'weekly':
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                week_interval = 7 * self.frequency_interval
                if days_since >= week_interval and days_since < (week_interval + 7):
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1
        elif self.frequency == 'monthly':
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                month_interval = 30 * self.frequency_interval
                if days_since >= month_interval and days_since < (month_interval + 30):
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1
        elif self.frequency == 'custom':
            if self.last_completed_date:
                days_since = (target_date - self.last_completed_date).days
                if days_since == 1:
                    self.streak_count += 1
                else:
                    self.streak_count = 1
            else:
                self.streak_count = 1

        self.last_completed_date = target_date
    
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

class Habit(db.Model):
    """Habit tracking model with positive/negative counters"""
    __tablename__ = 'habits'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.String(20), default='normal')  # easy, normal, hard
    count = db.Column(db.Integer, default=0)  # Can be positive or negative
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    position = db.Column(db.Integer, default=0)
    focused = db.Column(db.Boolean, default=False)
    last_increment_date = db.Column(db.Date, nullable=True)
    
    def __repr__(self):
        return f'<Habit {self.id}: {self.title}>'
    
    def get_max_count(self):
        """Get the maximum count for progress bar based on difficulty"""
        if self.difficulty == 'easy':
            return 30
        elif self.difficulty == 'hard':
            return 300
        else:  # normal
            return 100
    
    def get_progress_percentage(self):
        """Calculate progress percentage (capped at 100%)"""
        max_count = self.get_max_count()
        if self.count <= 0:
            return 0
        percentage = (self.count / max_count) * 100
        return min(100, percentage)
    
    def increment(self, target_date=None):
        """Increment count by 1 for the given date (defaults to today)."""
        self.count += 1
        self.last_increment_date = target_date or date.today()
    
    def decrement(self):
        """Decrement count by 1"""
        self.count -= 1
    
    def get_difficulty_icon(self):
        """Get Bootstrap icon for difficulty"""
        if self.difficulty == 'easy':
            return 'feather'
        elif self.difficulty == 'hard':
            return 'fire'
        else:  # normal
            return 'bullseye'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'difficulty': self.difficulty,
            'count': self.count,
            'max_count': self.get_max_count(),
            'progress_percentage': self.get_progress_percentage(),
            'created_at': self.created_at.isoformat(),
            'position': self.position,
            'focused': self.focused,
            'last_increment_date': self.last_increment_date.isoformat() if self.last_increment_date else None
        }
class Goal(db.Model):
    """Goal tracking model with milestones"""
    __tablename__ = 'goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='active')  # active, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationship to milestones
    milestones = db.relationship('Milestone', backref='goal', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Goal {self.id}: {self.title}>'
    
    def get_completed_milestones_count(self):
        """Get count of completed milestones"""
        return sum(1 for m in self.milestones if m.completed)
    
    def get_total_milestones_count(self):
        """Get total count of milestones"""
        return len(self.milestones)
    
    def get_progress_percentage(self):
        """Calculate progress percentage based on milestones"""
        total = self.get_total_milestones_count()
        if total == 0:
            return 0
        completed = self.get_completed_milestones_count()
        return (completed / total) * 100
    
    def is_completed(self):
        """Check if all milestones are completed"""
        if not self.milestones:
            return False
        return all(m.completed for m in self.milestones)
    
    def update_status(self):
        """Update goal status based on milestone completion"""
        if self.is_completed() and self.status != 'completed':
            self.status = 'completed'
            self.completed_at = datetime.utcnow()
        elif not self.is_completed() and self.status == 'completed':
            self.status = 'active'
            self.completed_at = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'milestones': [m.to_dict() for m in self.milestones],
            'progress_percentage': self.get_progress_percentage()
        }

class Milestone(db.Model):
    """Milestone model for goals"""
    __tablename__ = 'milestones'
    
    id = db.Column(db.Integer, primary_key=True)
    goal_id = db.Column(db.Integer, db.ForeignKey('goals.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    order = db.Column(db.Integer, default=0)  # For ordering milestones
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Milestone {self.id}: {self.title}>'
    
    def toggle_completion(self):
        """Toggle milestone completion status"""
        self.completed = not self.completed
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'goal_id': self.goal_id,
            'title': self.title,
            'completed': self.completed,
            'order': self.order,
            'created_at': self.created_at.isoformat()
        }

class ShoppingList(db.Model):
    """Shopping list model with title and text-based items"""
    __tablename__ = 'shopping_lists'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    items = db.Column(db.Text, nullable=True)  # Text field for list items
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ShoppingList {self.id}: {self.title}>'
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'items': self.items,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class RolloverState(db.Model):
    """Track per-user rollover processing to avoid double-shifting tasks"""
    __tablename__ = 'rollover_state'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    last_processed_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RolloverState user={self.user_id} last={self.last_processed_date}>'

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'last_processed_date': self.last_processed_date.isoformat() if self.last_processed_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class MasterCategory(db.Model):
    """Masterprompt category per user"""
    __tablename__ = 'master_categories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sections = db.relationship('MasterSection', backref='category', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<MasterCategory {self.id}: {self.name}>'


class MasterSection(db.Model):
    """Reusable masterprompt section grouped by category"""
    __tablename__ = 'master_sections'

    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('master_categories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<MasterSection {self.id}: {self.title}>'

class Idea(db.Model):
    """Idea model for storing ideas with notes, mindmaps, and files"""
    __tablename__ = 'ideas'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)  # Markdown notes
    mindmap_data = db.Column(db.Text, nullable=True)  # JSON mindmap data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    files = db.relationship('IdeaFile', backref='idea', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Idea {self.id}: {self.title}>'
    
    def get_mindmap_data(self):
        """Get mindmap data as dict"""
        if not self.mindmap_data:
            return None
        try:
            return json.loads(self.mindmap_data)
        except:
            return None
    
    def set_mindmap_data(self, data):
        """Set mindmap data from dict"""
        try:
            self.mindmap_data = json.dumps(data) if isinstance(data, dict) else data
        except:
            self.mindmap_data = data

class IdeaFile(db.Model):
    """File attachments for ideas"""
    __tablename__ = 'idea_files'
    
    id = db.Column(db.Integer, primary_key=True)
    idea_id = db.Column(db.Integer, db.ForeignKey('ideas.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(500), nullable=False)
    filesize = db.Column(db.Integer, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<IdeaFile {self.id}: {self.filename}>'