from typing import Optional
import uuid

from fastapi import Request

from app.models.audit import AuditEvent, AuthAuditLog
from app.repo.audit import AuditRepository


class AuditService:
    """Service xử lý ghi nhận nhật ký kiểm toán (Audit Logs)."""

    def __init__(self, audit_repo: AuditRepository) -> None:
        self.audit_repo = audit_repo

    async def log_auth_event(
        self,
        event: AuditEvent | str,
        user_id: Optional[uuid.UUID] = None,
        email_attempted: Optional[str] = None,
        request: Optional[Request] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        commit: bool = True,
    ) -> AuthAuditLog:
        """Ghi nhận một sự kiện xác thực hoặc phân quyền vào nhật ký kiểm toán."""
        client_ip = ip
        client_user_agent = user_agent

        if request:
            if not client_ip:
                forwarded = request.headers.get("x-forwarded-for")
                if forwarded:
                    client_ip = forwarded.split(",")[0].strip()
                elif request.client:
                    client_ip = request.client.host
            if not client_user_agent:
                client_user_agent = request.headers.get("user-agent")

        if client_ip:
            client_ip = client_ip[:50]
        if email_attempted:
            email_attempted = email_attempted[:255]

        event_str = event.value if isinstance(event, AuditEvent) else str(event)

        audit_entry = await self.audit_repo.create_log(
            event=event_str,
            user_id=user_id,
            email_attempted=email_attempted,
            ip=client_ip,
            user_agent=client_user_agent,
        )
        if commit:
            await self.audit_repo.commit()
            await self.audit_repo.refresh(audit_entry)
        return audit_entry
