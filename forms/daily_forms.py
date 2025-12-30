"""
Daily form classes.
"""
from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length


class DailyCreateForm(FlaskForm):
    """Form for creating a new daily entry."""

    content = TextAreaField(
        "Content",
        validators=[
            DataRequired(message="Content is required"),
            Length(max=10000, message="Content must be less than 10000 characters"),
        ],
    )


class DailyEditForm(DailyCreateForm):
    """Form for editing an existing daily entry."""

    pass
