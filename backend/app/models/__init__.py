"""SQLAlchemy ORM models package.

Import all models here so that Alembic autogenerate can discover them via Base.metadata.
"""

from app.db.base import Base, TimestampMixin

__all__ = ["Base", "TimestampMixin"]

