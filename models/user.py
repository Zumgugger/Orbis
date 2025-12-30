"""
User and authentication-related models
"""
import json
from datetime import date, datetime

from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    """User model for authentication"""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=True)
    profile_pic = db.Column(db.String(500), nullable=True)
    role = db.Column(db.String(20), default="user")  # 'admin' or 'user'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)
    oauth_token = db.Column(
        db.Text, nullable=True
    )  # Store OAuth token JSON (access+refresh)

    def __repr__(self) -> str:
        return f"<User {self.id}: {self.email}>"

    def get_oauth_token(self) -> dict | None:
        """Retrieve stored OAuth token as dict"""
        if not self.oauth_token:
            return None
        try:
            return json.loads(self.oauth_token)
        except Exception:
            return None

    def set_oauth_token(self, token: dict | str) -> None:
        """Store OAuth token (dict or string)"""
        try:
            self.oauth_token = json.dumps(token) if isinstance(token, dict) else token
        except Exception:
            self.oauth_token = token
        db.session.commit()

    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == "admin"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "google_id": self.google_id,
            "email": self.email,
            "name": self.name,
            "profile_pic": self.profile_pic,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class RolloverState(db.Model):
    """Track per-user rollover processing to avoid double-shifting tasks"""

    __tablename__ = "rollover_state"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    last_processed_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<RolloverState user={self.user_id} last={self.last_processed_date}>"

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "last_processed_date": self.last_processed_date.isoformat()
            if self.last_processed_date
            else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
