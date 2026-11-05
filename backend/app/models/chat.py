import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Intent, MessageSender

if TYPE_CHECKING:
    from app.models.knowledge import KnowledgeDocument
    from app.models.ticket import Ticket
    from app.models.user import AppUser


class ChatSession(Base):
    __tablename__ = "chat_session"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("app_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_resolved_by_bot: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
    )

    # Relationships
    user: Mapped["AppUser"] = relationship(
        "AppUser",
        back_populates="chat_sessions",
        lazy="selectin",
    )
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="chat_session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
        lazy="selectin",
    )
    ticket: Mapped[Optional["Ticket"]] = relationship(
        "Ticket",
        back_populates="chat_session",
        uselist=False,
        lazy="selectin",
    )


class ChatMessage(Base):
    __tablename__ = "chat_message"

    __table_args__ = (
        CheckConstraint(
            "sender IN ('USER', 'BOT')",
            name="ck_chat_message_sender_valid",
        ),
        CheckConstraint(
            "intent IS NULL OR intent IN ('KB_QUESTION', 'SIMPLE_TROUBLESHOOT', 'NEEDS_DEPARTMENT', 'SMALLTALK', 'UNCLEAR')",
            name="ck_chat_message_intent_valid",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    chat_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_session.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[MessageSender] = mapped_column(
        sa.Enum(MessageSender, native_enum=False, length=20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    intent: Mapped[Optional[Intent]] = mapped_column(
        sa.Enum(Intent, native_enum=False, length=50),
        nullable=True,
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    ticket_draft: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    chat_session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages",
    )
    sources: Mapped[list["MessageSource"]] = relationship(
        "MessageSource",
        back_populates="chat_message",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MessageSource(Base):
    __tablename__ = "message_source"

    chat_message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_message.id", ondelete="CASCADE"),
        primary_key=True,
    )
    knowledge_document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("knowledge_document.id", ondelete="CASCADE"),
        primary_key=True,
    )
    relevance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Relationships
    chat_message: Mapped["ChatMessage"] = relationship(
        "ChatMessage",
        back_populates="sources",
    )
    knowledge_document: Mapped["KnowledgeDocument"] = relationship(
        "KnowledgeDocument",
        back_populates="message_sources",
        lazy="selectin",
    )
