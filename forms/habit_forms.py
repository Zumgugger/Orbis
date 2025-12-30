"""
Habit form classes.
"""
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class HabitCreateForm(FlaskForm):
    """Form for creating a new habit."""

    name = StringField(
        "Name",
        validators=[
            DataRequired(message="Name is required"),
            Length(max=200, message="Name must be less than 200 characters"),
        ],
    )
    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(max=5000, message="Description must be less than 5000 characters"),
        ],
    )
    frequency = SelectField(
        "Frequency",
        choices=[
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        default="daily",
    )


class HabitEditForm(HabitCreateForm):
    """Form for editing an existing habit."""

    status = SelectField(
        "Status",
        choices=[
            ("active", "Active"),
            ("paused", "Paused"),
            ("completed", "Completed"),
        ],
        default="active",
    )
