"""
Idea form classes.
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, MultipleFileField
from wtforms import SelectField, StringField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class IdeaCreateForm(FlaskForm):
    """Form for creating a new idea."""

    title = StringField(
        "Title",
        validators=[
            DataRequired(message="Title is required"),
            Length(max=200, message="Title must be less than 200 characters"),
        ],
    )
    content = TextAreaField(
        "Content",
        validators=[
            Optional(),
            Length(max=50000, message="Content must be less than 50000 characters"),
        ],
    )
    category = SelectField(
        "Category",
        choices=[
            ("general", "General"),
            ("project", "Project"),
            ("business", "Business"),
            ("creative", "Creative"),
            ("technical", "Technical"),
            ("other", "Other"),
        ],
        default="general",
    )
    tags = StringField(
        "Tags",
        validators=[
            Optional(),
            Length(max=500, message="Tags must be less than 500 characters"),
        ],
    )
    files = MultipleFileField(
        "Files",
        validators=[
            Optional(),
            FileAllowed(
                ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt", "md"],
                "Only images, PDFs, and documents are allowed",
            ),
        ],
    )


class IdeaEditForm(IdeaCreateForm):
    """Form for editing an existing idea."""

    status = SelectField(
        "Status",
        choices=[
            ("draft", "Draft"),
            ("active", "Active"),
            ("archived", "Archived"),
        ],
        default="active",
    )
