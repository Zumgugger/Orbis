"""
Todo form classes.
"""
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TextAreaField, TimeField
from wtforms.validators import DataRequired, Length, Optional


class TodoCreateForm(FlaskForm):
    """Form for creating a new todo."""

    title = StringField(
        "Title",
        validators=[
            DataRequired(message="Title is required"),
            Length(max=200, message="Title must be less than 200 characters"),
        ],
    )
    description = TextAreaField(
        "Description",
        validators=[
            Optional(),
            Length(max=5000, message="Description must be less than 5000 characters"),
        ],
    )
    priority = SelectField(
        "Priority",
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
        ],
        default="medium",
    )
    due_date = DateField("Due Date", validators=[Optional()])
    due_time = TimeField("Due Time", validators=[Optional()])
    duration_minutes = StringField("Duration (minutes)", validators=[Optional()])


class TodoEditForm(TodoCreateForm):
    """Form for editing an existing todo."""

    status = SelectField(
        "Status",
        choices=[
            ("pending", "Pending"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
        ],
        default="pending",
    )
