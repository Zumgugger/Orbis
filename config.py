"""
Flask configuration classes.

These classes configure Flask and its extensions.
For application settings validation, see settings.py.
For logging configuration, see logging_config.py.
"""
import os

from settings import settings


class BaseConfig:
    # Load validated settings
    _settings = settings()

    SECRET_KEY = _settings.SECRET_KEY
    SQLALCHEMY_DATABASE_URI = _settings.DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = None  # Avoid unexpected expiry during long sessions
    MAX_CONTENT_LENGTH = _settings.max_file_size_bytes

    # Logging configuration
    LOG_LEVEL = "INFO"
    LOG_FILE = None  # Set to a path to enable file logging


class DevConfig(BaseConfig):
    DEBUG = True
    LOG_LEVEL = "DEBUG"


class ProdConfig(BaseConfig):
    DEBUG = False
    LOG_LEVEL = "INFO"
    LOG_FILE = os.getenv("LOG_FILE")  # Optional file logging in production

    # Secure cookie settings for HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_SSL_STRICT = False  # Allow CSRF to work behind reverse proxy


class TestConfig(BaseConfig):
    TESTING = True
    # Use in-memory DB by default for tests unless overridden
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    WTF_CSRF_ENABLED = False
    LOG_LEVEL = "WARNING"  # Less verbose during tests
