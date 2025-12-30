"""
Validation utilities for form inputs
Provides reusable validation functions with clear error messages
"""
from __future__ import annotations

from datetime import date, datetime, time
from functools import wraps
from typing import Any, Callable, TypeVar

from flask import flash

T = TypeVar("T")


class ValidationError(Exception):
    """Custom validation error with user-friendly message"""

    pass


def validate_required(value: Any, field_name: str = "Field") -> Any:
    """Validate that a field is not empty"""
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field_name} is required")
    return value.strip() if isinstance(value, str) else value


def validate_title(
    value: str | None,
    field_name: str = "Title",
    min_length: int = 1,
    max_length: int = 200,
) -> str:
    """Validate title field"""
    result = validate_required(value, field_name)
    if len(result) < min_length:
        raise ValidationError(f"{field_name} must be at least {min_length} characters")
    if len(result) > max_length:
        raise ValidationError(f"{field_name} must not exceed {max_length} characters")
    return result


def validate_text(
    value: str | None,
    field_name: str = "Text",
    max_length: int = 10000,
    required: bool = False,
) -> str:
    """Validate text/description field"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return ""

    result = value.strip() if isinstance(value, str) else str(value)
    if len(result) > max_length:
        raise ValidationError(f"{field_name} must not exceed {max_length} characters")
    return result


def validate_date(
    value: str | date | None,
    field_name: str = "Date",
    required: bool = False,
    allow_past: bool = True,
) -> date | None:
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
        except (ValueError, AttributeError) as exc:
            raise ValidationError(
                f"{field_name} must be a valid date (YYYY-MM-DD)"
            ) from exc

    # Check if date is in the past (if not allowed)
    if not allow_past and parsed_date < date.today():
        raise ValidationError(f"{field_name} cannot be in the past")

    return parsed_date


def validate_time(
    value: str | None, field_name: str = "Time", required: bool = False
) -> time | None:
    """Validate time field (accepts HH:MM string)"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    try:
        parsed_time = datetime.strptime(str(value).strip(), "%H:%M").time()
        return parsed_time
    except (ValueError, AttributeError) as exc:
        raise ValidationError(f"{field_name} must be a valid time (HH:MM)") from exc


def validate_choice(
    value: str | None,
    choices: list[str],
    field_name: str = "Field",
    required: bool = True,
) -> str | None:
    """Validate that value is in allowed choices"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return choices[0] if choices else None

    if value not in choices:
        raise ValidationError(f"{field_name} must be one of: {', '.join(choices)}")
    return value


def validate_priority(value: str | None) -> str:
    """Validate priority field"""
    return (
        validate_choice(value, ["low", "medium", "high"], "Priority", required=False)
        or "medium"
    )


def validate_difficulty(value: str | None) -> str:
    """Validate difficulty field"""
    return (
        validate_choice(value, ["easy", "normal", "hard"], "Difficulty", required=False)
        or "normal"
    )


def validate_frequency(value: str | None) -> str:
    """Validate frequency field"""
    return (
        validate_choice(
            value, ["daily", "weekly", "monthly", "custom"], "Frequency", required=False
        )
        or "daily"
    )


def validate_integer(
    value: int | str | None,
    field_name: str = "Value",
    min_val: int | None = None,
    max_val: int | None = None,
    required: bool = False,
) -> int | None:
    """Validate integer field"""
    if value is None or value == "":
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    try:
        int_value = int(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"{field_name} must be a valid number") from exc

    if min_val is not None and int_value < min_val:
        raise ValidationError(f"{field_name} must be at least {min_val}")
    if max_val is not None and int_value > max_val:
        raise ValidationError(f"{field_name} must not exceed {max_val}")

    return int_value


def validate_duration(
    hours: int | str | None, minutes: int | str | None, field_name: str = "Duration"
) -> tuple[int, int]:
    """Validate duration hours and minutes"""
    try:
        h = validate_integer(hours, f"{field_name} hours", min_val=0, max_val=23) or 0
        m = (
            validate_integer(minutes, f"{field_name} minutes", min_val=0, max_val=59)
            or 0
        )
    except ValidationError:
        raise

    if h == 0 and m == 0:
        raise ValidationError(f"{field_name} must be greater than 0 minutes")

    return h, m


def validate_email(
    value: str | None, field_name: str = "Email", required: bool = True
) -> str | None:
    """Basic email validation"""
    if not value:
        if required:
            raise ValidationError(f"{field_name} is required")
        return None

    result = value.strip()
    if "@" not in result or "." not in result.split("@")[-1]:
        raise ValidationError(f"{field_name} must be a valid email address")

    if len(result) > 255:
        raise ValidationError(f"{field_name} is too long")

    return result


def validate_weekdays(value: list[str] | None, required: bool = False) -> list[str]:
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


def flash_validation_error(
    error: ValidationError | str, category: str = "error"
) -> None:
    """Flash a validation error message"""
    flash(str(error), category)


def handle_validation(form_handler: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to handle validation errors in form routes
    Usage:
        @handle_validation
        def my_route():
            title = validate_title(request.form.get('title'))
            # ... more validation
    """

    @wraps(form_handler)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return form_handler(*args, **kwargs)
        except ValidationError as e:
            flash_validation_error(e)
            # Return to the same page (caller should handle redirect)
            raise

    return wrapper
