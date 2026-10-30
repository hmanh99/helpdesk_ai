"""SQLAlchemy ORM models package.

Import all models here so that Alembic autogenerate can discover them via Base.metadata.
"""

from app.db.base import Base, TimestampMixin
from app.models.audit import AuditEvent, AuthAuditLog
from app.models.department import Department
from app.models.user import AppUser, UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "Department",
    "AppUser",
    "UserRole",
    "AuthAuditLog",
    "AuditEvent",
]
