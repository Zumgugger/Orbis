"""
Flask configuration classes.

These classes configure Flask and its extensions.
For application settings validation, see settings.py.
"""
import logging
import os

from settings import settings


class RequestFormatter(logging.Formatter):
    def format(self, record):
        try:
            from flask import has_request_context, request
            from flask_login import current_user

            if has_request_context():
                record.path = request.path
                record.method = request.method
                record.remote_addr = request.remote_addr
            else:
                record.path = None
                record.method = None
                record.remote_addr = None
            record.user_id = getattr(current_user, "id", None)
        except Exception:
            record.path = None
            record.method = None
            record.remote_addr = None
            record.user_id = None
        return super().format(record)


class BaseConfig:
    # Load validated settings
    _settings = settings()

    SECRET_KEY = _settings.SECRET_KEY
    SQLALCHEMY_DATABASE_URI = _settings.DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_TIME_LIMIT = None  # Avoid unexpected expiry during long sessions
    MAX_CONTENT_LENGTH = _settings.max_file_size_bytes

    @staticmethod
    def configure_logging(app):
        handler = logging.StreamHandler()
        formatter = RequestFormatter(
            fmt=(
                "%(asctime)s %(levelname)s "
                "path=%(path)s method=%(method)s user=%(user_id)s "
                "msg=%(message)s"
            )
        )
        handler.setFormatter(formatter)
        if not app.logger.handlers:
            app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)


class DevConfig(BaseConfig):
    DEBUG = True


class ProdConfig(BaseConfig):
    DEBUG = False


class TestConfig(BaseConfig):
    TESTING = True
    # Use in-memory DB by default for tests unless overridden
    SQLALCHEMY_DATABASE_URI = os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    WTF_CSRF_ENABLED = False
