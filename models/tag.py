"""
Tag model for cross-entity tagging system
"""
from datetime import datetime

from extensions import db

# Predefined color palette for tags (outline colors)
TAG_COLORS = [
    "#6366f1",  # Indigo
    "#8b5cf6",  # Violet
    "#ec4899",  # Pink
    "#ef4444",  # Red
    "#f97316",  # Orange
    "#eab308",  # Yellow
    "#22c55e",  # Green
    "#14b8a6",  # Teal
    "#06b6d4",  # Cyan
    "#3b82f6",  # Blue
    "#6b7280",  # Gray
    "#a855f7",  # Purple
]

# Smart tag keywords mapping
SMART_TAG_KEYWORDS = {
    "work": [
        "meeting",
        "project",
        "deadline",
        "report",
        "presentation",
        "client",
        "office",
        "email",
        "task",
    ],
    "personal": [
        "home",
        "family",
        "friend",
        "birthday",
        "anniversary",
        "vacation",
        "hobby",
    ],
    "health": [
        "exercise",
        "gym",
        "workout",
        "run",
        "walk",
        "meditation",
        "yoga",
        "doctor",
        "medicine",
        "sleep",
    ],
    "finance": [
        "pay",
        "bill",
        "budget",
        "money",
        "bank",
        "invoice",
        "expense",
        "savings",
        "investment",
    ],
    "learning": [
        "learn",
        "study",
        "read",
        "course",
        "book",
        "tutorial",
        "practice",
        "skill",
    ],
    "shopping": ["buy", "shop", "order", "groceries", "amazon", "store", "purchase"],
    "urgent": ["urgent", "asap", "immediately", "important", "critical", "priority"],
    "creative": ["design", "write", "create", "art", "music", "idea", "brainstorm"],
    "tech": [
        "code",
        "programming",
        "software",
        "app",
        "website",
        "bug",
        "feature",
        "deploy",
    ],
    "admin": ["organize", "clean", "file", "paperwork", "document", "backup", "update"],
}


class Tag(db.Model):
    """Tag model for organizing entities"""

    __tablename__ = "tags"
    __table_args__ = (
        db.UniqueConstraint("user_id", "name", name="uq_tag_user_name"),
        db.Index("ix_tags_user_name", "user_id", "name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(20), default="#6366f1")  # Hex color for outline
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships to entity tags
    entity_tags = db.relationship(
        "EntityTag", backref="tag", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Tag {self.id}: {self.name}>"

    def get_usage_count(self) -> int:
        """Get total usage count across all entities"""
        return self.entity_tags.count()

    def get_usage_by_type(self) -> dict:
        """Get usage count per entity type"""
        counts = {}
        for et in self.entity_tags:
            counts[et.entity_type] = counts.get(et.entity_type, 0) + 1
        return counts

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "usage_count": self.get_usage_count(),
        }

    @staticmethod
    def get_smart_tag_suggestions(
        text: str, existing_tags: list[str] = None
    ) -> list[str]:
        """Get smart tag suggestions based on text content"""
        if not text:
            return []

        existing_tags = existing_tags or []
        text_lower = text.lower()
        suggestions = []

        for tag_name, keywords in SMART_TAG_KEYWORDS.items():
            if tag_name in existing_tags:
                continue
            for keyword in keywords:
                if keyword in text_lower:
                    suggestions.append(tag_name)
                    break

        return suggestions[:5]  # Limit to 5 suggestions


class EntityTag(db.Model):
    """Association table for tags and entities (polymorphic)"""

    __tablename__ = "entity_tags"
    __table_args__ = (
        db.UniqueConstraint("tag_id", "entity_type", "entity_id", name="uq_entity_tag"),
        db.Index("ix_entity_tags_entity", "entity_type", "entity_id"),
        db.Index("ix_entity_tags_tag", "tag_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    tag_id = db.Column(
        db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )
    entity_type = db.Column(
        db.String(20), nullable=False
    )  # 'todo', 'idea', 'goal', 'daily', 'habit', 'note'
    entity_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<EntityTag {self.tag_id} -> {self.entity_type}:{self.entity_id}>"


# Helper functions for entity models
def get_tags_for_entity(user_id: int, entity_type: str, entity_id: int) -> list[Tag]:
    """Get all tags for a specific entity"""
    return (
        Tag.query.join(EntityTag)
        .filter(
            Tag.user_id == user_id,
            EntityTag.entity_type == entity_type,
            EntityTag.entity_id == entity_id,
        )
        .all()
    )


def add_tag_to_entity(tag: Tag, entity_type: str, entity_id: int) -> EntityTag:
    """Add a tag to an entity"""
    existing = EntityTag.query.filter_by(
        tag_id=tag.id, entity_type=entity_type, entity_id=entity_id
    ).first()

    if existing:
        return existing

    entity_tag = EntityTag(tag_id=tag.id, entity_type=entity_type, entity_id=entity_id)
    db.session.add(entity_tag)
    return entity_tag


def remove_tag_from_entity(tag_id: int, entity_type: str, entity_id: int) -> bool:
    """Remove a tag from an entity"""
    entity_tag = EntityTag.query.filter_by(
        tag_id=tag_id, entity_type=entity_type, entity_id=entity_id
    ).first()

    if entity_tag:
        db.session.delete(entity_tag)
        return True
    return False


def sync_entity_tags(
    user_id: int, entity_type: str, entity_id: int, tag_ids: list[int]
) -> None:
    """Sync tags for an entity - removes old, adds new"""
    # Remove existing tags not in the new list
    EntityTag.query.filter(
        EntityTag.entity_type == entity_type,
        EntityTag.entity_id == entity_id,
        ~EntityTag.tag_id.in_(tag_ids) if tag_ids else True,
    ).delete(synchronize_session=False)

    # Add new tags
    for tag_id in tag_ids:
        tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
        if tag:
            add_tag_to_entity(tag, entity_type, entity_id)


def get_entities_by_tag(
    user_id: int, tag_id: int, entity_type: str = None
) -> list[int]:
    """Get entity IDs that have a specific tag"""
    query = EntityTag.query.join(Tag).filter(
        Tag.user_id == user_id, EntityTag.tag_id == tag_id
    )

    if entity_type:
        query = query.filter(EntityTag.entity_type == entity_type)

    return [(et.entity_type, et.entity_id) for et in query.all()]
