import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.department import Department


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    STAFF = "STAFF"
    TECHNICIAN = "TECHNICIAN"
    DEPT_MANAGER = "DEPT_MANAGER"
    ADMIN = "ADMIN"


class AppUser(Base, TimestampMixin):
    __tablename__ = "app_user"

    __table_args__ = (
        Index("ix_app_user_email_lower", sa.text("lower(email)"), unique=True),
        CheckConstraint(
            "role IN ('STUDENT', 'STAFF', 'TECHNICIAN', 'DEPT_MANAGER', 'ADMIN')",
            name="ck_app_user_role_valid",
        ),
        CheckConstraint(
            "(role NOT IN ('TECHNICIAN', 'DEPT_MANAGER')) OR (department_id IS NOT NULL)",
            name="ck_app_user_tech_dept_mgr_has_dept",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("department.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[UserRole] = mapped_column(
        sa.Enum(UserRole, native_enum=False, length=50),
        nullable=False,
        default=UserRole.STUDENT,
    )
    is_active: Mapped[bool] = mapped_column(
        default=True,
        server_default="true",
        nullable=False,
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="members",
        lazy="selectin",
    )
