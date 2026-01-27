"""
Database models package
Re-exports all models for convenient importing
"""
from models.api_key import ApiKey
from models.daily import CompletionLog, Daily
from models.goal import Goal, Milestone
from models.habit import Habit, HabitLog
from models.idea import Idea, IdeaFile
from models.masterprompt import MasterCategory, MasterSection
from models.note import Note, NoteCategory, NoteType
from models.shared_title import SharedTitle
from models.shopping import ShoppingList
from models.stats import DailyStats
from models.tag import (
    SMART_TAG_KEYWORDS,
    TAG_COLORS,
    EntityTag,
    Tag,
    add_tag_to_entity,
    get_entities_by_tag,
    get_tags_for_entity,
    remove_tag_from_entity,
    sync_entity_tags,
)
from models.todo import Todo
from models.user import RolloverState, User

__all__ = [
    "User",
    "RolloverState",
    "ApiKey",
    "Todo",
    "Daily",
    "CompletionLog",
    "Habit",
    "HabitLog",
    "Goal",
    "Milestone",
    "ShoppingList",
    "Idea",
    "IdeaFile",
    "MasterCategory",
    "MasterSection",
    "Note",
    "NoteCategory",
    "NoteType",
    "SharedTitle",
    "Tag",
    "EntityTag",
    "TAG_COLORS",
    "SMART_TAG_KEYWORDS",
    "get_tags_for_entity",
    "add_tag_to_entity",
    "remove_tag_from_entity",
    "sync_entity_tags",
    "get_entities_by_tag",
    "DailyStats",
]
