"""SQLAlchemy ORM models package.

Import all models here so that Alembic autogenerate can discover them via Base.metadata.
"""

from app.db.base import Base, TimestampMixin
from app.models.audit import AuditEvent, AuthAuditLog
from app.models.category import Category
from app.models.chat import ChatMessage, ChatSession, MessageSource
from app.models.department import Department
from app.models.enums import (
    Channel,
    Intent,
    MessageSender,
    Priority,
    ProcessingStatus,
    TicketStatus,
)
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.ticket import (
    AIClassification,
    Ticket,
    TicketComment,
    TicketHistory,
)
from app.models.user import AppUser, UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "Department",
    "Category",
    "KnowledgeDocument",
    "KnowledgeChunk",
    "ChatSession",
    "ChatMessage",
    "MessageSource",
    "Ticket",
    "TicketHistory",
    "TicketComment",
    "AIClassification",
    "AppUser",
    "UserRole",
    "AuthAuditLog",
    "AuditEvent",
    "TicketStatus",
    "Priority",
    "Channel",
    "MessageSender",
    "Intent",
    "ProcessingStatus",
]
