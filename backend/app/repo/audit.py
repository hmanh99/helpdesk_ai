from typing import Optional
import uuid

from app.models.audit import AuthAuditLog
from app.repo.base import BaseRepository


class AuditRepository(BaseRepository):
    """Repository quản lý các thao tác cơ sở dữ liệu đối với nhật ký bảo mật (AuthAuditLog)."""

    async def create_log(
        self,
        event: str,
        user_id: Optional[uuid.UUID] = None,
        email_attempted: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuthAuditLog:
        """Tạo một bản ghi nhật ký kiểm toán mới."""
        audit_entry = AuthAuditLog(
            user_id=user_id,
            email_attempted=email_attempted,
            event=event,
            ip=ip,
            user_agent=user_agent,
        )
        self.db.add(audit_entry)
        return audit_entry
