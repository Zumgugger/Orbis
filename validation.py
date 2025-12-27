"""
Validation utilities for form inputs
Provides reusable validation functions with clear error messages
"""
from datetime import date, datetime

from flask import flash


class ValidationError(Exception):
    """Custom validation error with user-friendly message"""

    pass


def validate_required(value, field_name="Field"):
    """Validate that a field is not empty"""
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required")
    return value.strip() if isinstance(value, str) else value


def validate_title(value, field_name="Title", min_length=1, max_length=200):
    """Validate title field"""
    value = validate_required(value, field_name)
    if len(value) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters")
    if len(value) > max_length:
        raise ValidationError(f"{field_name} must not exceed {max_length} characters")
    return value


def validate_text(value, field_name="Text", max_length=10000, required=False):
    """Validate text/description field"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return ""

    value = value.strip() if isinstance(value, str) else str(value)
    if len(value) > max_length:
        raise ValidationError(f"{field_name} must not exceed {max_length} characters")
    return value


def validate_date(value, field_name="Date", required=False, allow_past=True):
    """Validate date field (accepts YYYY-MM-DD string or date object)"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    # If already a date object, validate it
    if isinstance(value, date):
        parsed_date = value
    else:
        # Parse string
        try:
            parsed_date = datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
        except (ValueError, AttributeError):
            raise ValidationError(f"{field_name} must be a valid date (YYYY-MM-DD)")

    # Check if date is in the past (if not allowed)
    if not allow_past and parsed_date < date.today():
        raise ValidationError(f"{field_name} cannot be in the past")

    return parsed_date


def validate_time(value, field_name="Time", required=False):
    """Validate time field (accepts HH:MM string)"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    try:
        parsed_time = datetime.strptime(str(value).strip(), "%H:%M").time()
        return parsed_time
    except (ValueError, AttributeError):
        raise ValidationError(f"{field_name} must be a valid time (HH:MM)")


def validate_choice(value, choices, field_name="Field", required=True):
    """Validate that value is in allowed choices"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return choices[0] if choices else None

    if value not in choices:
        raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}")
    return value


def validate_priority(value):
    """Validate priority field"""
    return (
        validate_choice(value, ["low", "medium", "high"], "Priority", required=False)
        or "medium"
    )


def validate_difficulty(value):
    """Validate difficulty field"""
    return (
        validate_choice(value, ["easy", "normal", "hard"], "Difficulty", required=False)
        or "normal"
    )


def validate_frequency(value):
    """Validate frequency field"""
    return (
        validate_choice(
            value, ["daily", "weekly", "monthly", "custom"], "Frequency", required=False
        )
        or "daily"
    )


def validate_integer(
    value, field_name="Value", min_val=None, max_val=None, required=False
):
    """Validate integer field"""
    if value is None or value == "":
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid number")

    if min_val is not None and int_value < min_val:
        raise ValidationError(f"{field_name} must be at least {min_val}")
    if max_val is not None and int_value > max_val:
        raise ValidationError(f"{field_name} must not exceed {max_val}")

    return int_value


def validate_duration(hours, minutes, field_name="Duration"):
    """Validate duration hours and minutes"""
    try:
        h = validate_integer(hours, f"{field_name} hours", min_val=0, max_val=23) or 0
        m = (
            validate_integer(minutes, f"{field_name} minutes", min_val=0, max_val=59)
            or 0
        )
    except ValidationError as e:
        raise ValidationError(str(e))

    if h == 0 and m == 0:
        raise ValidationError(f"{field_name} must be greater than 0 minutes")

    return h, m


def validate_email(value, field_name="Email", required=True):
    """Basic email validation"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    value = value.strip()
    if "@" not in value or "." not in value.split("@")[-1]:
        raise ValidationError(f"{field_name} must be a valid email address")

    if len(value) > 255:
        raise ValidationError(f"{field_name} is too long")

    return value


def validate_weekdays(value, required=False):
    """Validate weekday selection"""
    valid_days = [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    ]

    if not value or not isinstance(value, list):
        if required:
            raise ValidationError("At least one weekday must be selected")
        return []

    # Ensure all selected days are valid
    for day in value:
        if day not in valid_days:
            raise ValidationError(f"Invalid weekday: {day}")

    return value


def flash_validation_error(error, category="error"):
    """Flash a validation error message"""
    flash(str(error), category)


def handle_validation(form_handler):
    """
    Decorator to handle validation errors in form routes
    Usage:
        @handle_validation
        def my_route():
            title = validate_title(request.form.get('title'))
            # ... more validation
    """
    from functools import wraps

    @wraps(form_handler)
    def wrapper(*args, **kwargs):
        try:
            return form_handler(*args, **kwargs)
        except ValidationError as e:
            flash_validation_error(e)
            # Return to the same page (caller should handle redirect)
            raise

    return wrapper
