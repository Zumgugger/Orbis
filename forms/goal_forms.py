"""
Goal form classes.
"""
from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class GoalCreateForm(FlaskForm):
    """Form for creating a new goal."""

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
    category = SelectField(
        "Category",
        choices=[
            ("personal", "Personal"),
            ("career", "Career"),
            ("health", "Health"),
            ("finance", "Finance"),
            ("education", "Education"),
            ("other", "Other"),
        ],
        default="personal",
    )
    target_date = DateField("Target Date", validators=[Optional()])


class GoalEditForm(GoalCreateForm):
    """Form for editing an existing goal."""

    status = SelectField(
        "Status",
        choices=[
            ("active", "Active"),
            ("completed", "Completed"),
            ("abandoned", "Abandoned"),
        ],
        default="active",
    )


class MilestoneForm(FlaskForm):
    """Form for creating/editing a milestone."""

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
            Length(max=2000, message="Description must be less than 2000 characters"),
        ],
    )
    target_date = DateField("Target Date", validators=[Optional()])
