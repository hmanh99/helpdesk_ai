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
    Index,
    JSON,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Channel, Priority, TicketStatus

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.chat import ChatSession
    from app.models.department import Department
    from app.models.user import AppUser


class Ticket(Base):
    __tablename__ = "ticket"

    __table_args__ = (
        CheckConstraint(
            "status IN ('NEW', 'TRIAGED', 'ASSIGNED', 'IN_PROGRESS', 'PENDING_USER', 'RESOLVED', 'CLOSED', 'CANCELLED')",
            name="ck_ticket_status_valid",
        ),
        CheckConstraint(
            "priority IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_ticket_priority_valid",
        ),
        CheckConstraint(
            "channel IN ('CHATBOT', 'WEB_FORM')",
            name="ck_ticket_channel_valid",
        ),
        Index("ix_ticket_requester_id", "requester_id"),
        Index("ix_ticket_department_id", "department_id"),
        Index("ix_ticket_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("app_user.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assignee_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("department.id", ondelete="SET NULL"),
        nullable=True,
    )
    chat_session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("chat_session.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    priority: Mapped[Priority] = mapped_column(
        sa.Enum(Priority, native_enum=False, length=20),
        default=Priority.MEDIUM,
        server_default="MEDIUM",
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        sa.Enum(TicketStatus, native_enum=False, length=30),
        default=TicketStatus.NEW,
        server_default="NEW",
        nullable=False,
    )
    channel: Mapped[Channel] = mapped_column(
        sa.Enum(Channel, native_enum=False, length=20),
        default=Channel.WEB_FORM,
        server_default="WEB_FORM",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    requester: Mapped["AppUser"] = relationship(
        "AppUser",
        foreign_keys=[requester_id],
        back_populates="tickets_requested",
        lazy="selectin",
    )
    assignee: Mapped[Optional["AppUser"]] = relationship(
        "AppUser",
        foreign_keys=[assignee_id],
        back_populates="tickets_assigned",
        lazy="selectin",
    )
    category: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="tickets",
        lazy="selectin",
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="tickets",
        lazy="selectin",
    )
    chat_session: Mapped[Optional["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="ticket",
    )
    histories: Mapped[list["TicketHistory"]] = relationship(
        "TicketHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketHistory.changed_at",
        lazy="selectin",
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at",
    )
    classifications: Mapped[list["AIClassification"]] = relationship(
        "AIClassification",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="AIClassification.created_at.desc()",
        lazy="selectin",
    )


class TicketHistory(Base):
    __tablename__ = "ticket_history"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    changed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("app_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    old_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    new_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="histories",
    )
    actor: Mapped[Optional["AppUser"]] = relationship(
        "AppUser",
        lazy="selectin",
    )


class TicketComment(Base):
    __tablename__ = "ticket_comment"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("app_user.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_internal: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="comments",
    )
    author: Mapped["AppUser"] = relationship(
        "AppUser",
        lazy="selectin",
    )


class AIClassification(Base):
    __tablename__ = "ai_classification"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("ticket.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predicted_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("category.id", ondelete="SET NULL"),
        nullable=True,
    )
    suggested_priority: Mapped[Optional[Priority]] = mapped_column(
        sa.Enum(Priority, native_enum=False, length=20),
        nullable=True,
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    raw_output: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="classifications",
    )
    predicted_category: Mapped[Optional["Category"]] = relationship(
        "Category",
        lazy="selectin",
    )

    def is_low_confidence(self, threshold: float = 0.6) -> bool:
        return self.confidence_score < threshold
