"""
API Key model for external API access
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import TYPE_CHECKING

from extensions import db

if TYPE_CHECKING:
    pass


class ApiKey(db.Model):
    """API Key model for managing external API access"""

    __tablename__ = "api_keys"
    __table_args__ = (
        db.Index("ix_api_keys_user", "user_id"),
        db.UniqueConstraint("user_id", name="uq_api_key_user"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    key_hash = db.Column(db.String(64), nullable=False, unique=True)  # SHA-256 hash
    key_prefix = db.Column(
        db.String(12), nullable=False
    )  # First 12 chars (orb_xxxxxxxx)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)
    requests_this_hour = db.Column(db.Integer, default=0)
    hour_started_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="api_key", uselist=False)

    def __repr__(self) -> str:
        return f"<ApiKey {self.key_prefix}...>"

    @staticmethod
    def generate_key() -> str:
        """Generate a new API key (orb_ prefix + 32 random alphanumeric chars)"""
        random_part = secrets.token_urlsafe(24)[:32]  # 32 chars of alphanumeric
        return f"orb_{random_part}"

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key using SHA-256"""
        return hashlib.sha256(key.encode()).hexdigest()

    @staticmethod
    def create_for_user(user_id: int) -> tuple[str, ApiKey]:
        """Create a new API key for a user. Returns (plain_key, api_key_object)"""
        # Delete old key if exists
        ApiKey.query.filter_by(user_id=user_id).delete()

        plain_key = ApiKey.generate_key()
        key_hash = ApiKey.hash_key(plain_key)
        key_prefix = plain_key[:12]  # orb_xxxxxxxx

        api_key = ApiKey(
            user_id=user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
        )
        db.session.add(api_key)
        db.session.commit()

        return plain_key, api_key

    @staticmethod
    def verify_key(key: str) -> ApiKey | None:
        """Verify an API key and return the ApiKey object if valid"""
        if not key or not key.startswith("orb_"):
            return None

        key_hash = ApiKey.hash_key(key)
        return ApiKey.query.filter_by(key_hash=key_hash).first()

    def record_request(self) -> None:
        """Record an API request and update rate limit counters"""
        now = datetime.utcnow()
        hour_ago = None

        if self.hour_started_at:
            from datetime import timedelta

            hour_ago = self.hour_started_at + timedelta(hours=1)

        # Reset counter if hour has passed
        if not self.hour_started_at or now >= hour_ago:
            self.requests_this_hour = 0
            self.hour_started_at = now

        self.requests_this_hour += 1
        self.last_used_at = now
        db.session.commit()

    def get_requests_remaining(self) -> int:
        """Get remaining requests in current hour (max 10)"""
        return max(0, 10 - self.requests_this_hour)

    def is_rate_limited(self) -> bool:
        """Check if key has exceeded rate limit"""
        return self.requests_this_hour >= 10

    def get_reset_time(self) -> datetime:
        """Get when rate limit resets"""
        from datetime import timedelta

        if self.hour_started_at:
            return self.hour_started_at + timedelta(hours=1)
        return datetime.utcnow()
