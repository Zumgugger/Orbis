"""
Shopping list form classes.
"""
from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, StringField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class ShoppingListForm(FlaskForm):
    """Form for creating/editing a shopping list item."""

    item_name = StringField(
        "Item Name",
        validators=[
            DataRequired(message="Item name is required"),
            Length(max=200, message="Item name must be less than 200 characters"),
        ],
    )
    quantity = IntegerField(
        "Quantity",
        validators=[
            Optional(),
            NumberRange(min=1, max=9999, message="Quantity must be between 1 and 9999"),
        ],
        default=1,
    )
    unit = StringField(
        "Unit",
        validators=[
            Optional(),
            Length(max=50, message="Unit must be less than 50 characters"),
        ],
    )
    category = SelectField(
        "Category",
        choices=[
            ("groceries", "Groceries"),
            ("household", "Household"),
            ("electronics", "Electronics"),
            ("clothing", "Clothing"),
            ("other", "Other"),
        ],
        default="groceries",
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
