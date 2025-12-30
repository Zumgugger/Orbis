"""
Centralized logging configuration for Orbis application.

Provides structured logging with consistent formatting across the application.
"""
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Any

from flask import Flask, g, has_request_context, request


class ContextFilter(logging.Filter):
    """Add request context to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context information to log record."""
        if has_request_context():
            record.url = request.url
            record.method = request.method
            record.remote_addr = request.remote_addr
            record.user_id = getattr(g, "user_id", None)
            record.request_id = getattr(g, "request_id", None)
        else:
            record.url = None
            record.method = None
            record.remote_addr = None
            record.user_id = None
            record.request_id = None
        return True


class StructuredFormatter(logging.Formatter):
    """JSON-like structured log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured output."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add request context if available
        if hasattr(record, "url") and record.url:
            log_data["request"] = {
                "url": record.url,
                "method": record.method,
                "remote_addr": record.remote_addr,
                "user_id": record.user_id,
                "request_id": record.request_id,
            }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data

        return str(log_data)


class SimpleFormatter(logging.Formatter):
    """Simple human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for human readability."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        base = (
            f"[{timestamp}] {record.levelname:8} {record.name}: {record.getMessage()}"
        )

        # Add request context if available
        if hasattr(record, "url") and record.url:
            base += f" | {record.method} {record.url}"

        # Add exception if present
        if record.exc_info:
            base += f"\n{self.formatException(record.exc_info)}"

        return base


def configure_logging(app: Flask) -> None:
    """
    Configure logging for the Flask application.

    Args:
        app: Flask application instance
    """
    # Get log level from config
    log_level_name = app.config.get("LOG_LEVEL", "INFO")
    log_level = getattr(logging, log_level_name.upper(), logging.INFO)

    # Remove default handlers
    app.logger.handlers.clear()

    # Create context filter
    context_filter = ContextFilter()

    # Choose formatter based on environment
    if app.debug:
        formatter = SimpleFormatter()
    else:
        formatter = StructuredFormatter()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(context_filter)
    app.logger.addHandler(console_handler)

    # File handler for production
    log_file = app.config.get("LOG_FILE")
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(StructuredFormatter())  # Always structured in files
        file_handler.addFilter(context_filter)
        app.logger.addHandler(file_handler)

    # Set log level
    app.logger.setLevel(log_level)

    # Log startup
    app.logger.info(f"Logging configured at level {log_level_name}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with the application's configuration.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    # Add context filter if not already present
    if not any(isinstance(f, ContextFilter) for f in logger.filters):
        logger.addFilter(ContextFilter())
    return logger


class LoggerMixin:
    """Mixin class to add logging capability to any class."""

    @property
    def logger(self) -> logging.Logger:
        """Get a logger for this class."""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__)
        return self._logger


def log_info(message: str, extra: dict[str, Any] | None = None) -> None:
    """Log an info message with optional extra data."""
    from flask import current_app

    logger = getattr(current_app, "logger", logging.getLogger(__name__))
    if extra:
        logger.info(message, extra={"extra_data": extra})
    else:
        logger.info(message)


def log_warning(message: str, extra: dict[str, Any] | None = None) -> None:
    """Log a warning message with optional extra data."""
    from flask import current_app

    logger = getattr(current_app, "logger", logging.getLogger(__name__))
    if extra:
        logger.warning(message, extra={"extra_data": extra})
    else:
        logger.warning(message)


def log_error(message: str, extra: dict[str, Any] | None = None) -> None:
    """Log an error message with optional extra data."""
    from flask import current_app

    logger = getattr(current_app, "logger", logging.getLogger(__name__))
    if extra:
        logger.error(message, extra={"extra_data": extra})
    else:
        logger.error(message)


def log_exception(
    exc: Exception, message: str | None = None, extra: dict[str, Any] | None = None
) -> None:
    """Log an exception with full traceback."""
    from flask import current_app

    logger = getattr(current_app, "logger", logging.getLogger(__name__))
    msg = message or str(exc)
    if extra:
        logger.exception(msg, extra={"extra_data": extra})
    else:
        logger.exception(msg)


def log_debug(message: str, extra: dict[str, Any] | None = None) -> None:
    """Log a debug message with optional extra data."""
    from flask import current_app

    logger = getattr(current_app, "logger", logging.getLogger(__name__))
    if extra:
        logger.debug(message, extra={"extra_data": extra})
    else:
        logger.debug(message)
