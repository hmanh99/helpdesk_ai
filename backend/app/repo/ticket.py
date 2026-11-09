from typing import Optional, Sequence
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from app.models.ticket import AIClassification, Ticket, TicketComment, TicketHistory
from app.models.user import AppUser, UserRole
from app.repo.base import BaseRepository


class TicketRepository(BaseRepository):
    """Repository quản lý cơ sở dữ liệu cho Ticket, TicketHistory, TicketComment và AIClassification."""

    async def get_by_id(self, ticket_id: uuid.UUID) -> Optional[Ticket]:
        result = await self.db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.requester),
                selectinload(Ticket.assignee),
                selectinload(Ticket.category),
                selectinload(Ticket.department),
                selectinload(Ticket.histories).selectinload(TicketHistory.actor),
                selectinload(Ticket.comments).selectinload(TicketComment.author),
                selectinload(Ticket.classifications).selectinload(AIClassification.predicted_category),
            )
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def get_by_chat_session_id(self, session_id: uuid.UUID) -> Optional[Ticket]:
        result = await self.db.execute(
            select(Ticket)
            .options(
                selectinload(Ticket.requester),
                selectinload(Ticket.assignee),
                selectinload(Ticket.category),
                selectinload(Ticket.department),
            )
            .where(Ticket.chat_session_id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_tickets_for_user(
        self,
        user: AppUser,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        unassigned_only: bool = False,
        assigned_to_me: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Ticket]:
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.requester),
                selectinload(Ticket.assignee),
                selectinload(Ticket.category),
                selectinload(Ticket.department),
            )
            .order_by(Ticket.created_at.desc())
        )

        # Lọc quyền truy cập theo vai trò
        if user.role == UserRole.ADMIN:
            pass  # Admin xem tất cả
        elif user.role in (UserRole.DEPT_MANAGER, UserRole.TECHNICIAN):
            # Xem ticket thuộc phòng ban mình hoặc do mình tạo/được phân công
            conditions = [
                Ticket.requester_id == user.id,
                Ticket.assignee_id == user.id,
            ]
            if user.department_id:
                conditions.append(Ticket.department_id == user.department_id)
            stmt = stmt.where(or_(*conditions))
        else:
            # STUDENT và STAFF chỉ xem ticket do chính mình tạo
            stmt = stmt.where(Ticket.requester_id == user.id)

        # Bộ lọc bổ sung
        if status:
            stmt = stmt.where(Ticket.status == status)
        if category_id:
            stmt = stmt.where(Ticket.category_id == category_id)
        if department_id:
            stmt = stmt.where(Ticket.department_id == department_id)
        if unassigned_only:
            stmt = stmt.where(Ticket.assignee_id.is_(None))
        if assigned_to_me:
            stmt = stmt.where(Ticket.assignee_id == user.id)

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_ticket(self, ticket: Ticket) -> Ticket:
        self.db.add(ticket)
        return ticket

    async def add_history(self, history: TicketHistory) -> TicketHistory:
        self.db.add(history)
        return history

    async def add_classification(self, classification: AIClassification) -> AIClassification:
        self.db.add(classification)
        return classification

    async def add_comment(self, comment: TicketComment) -> TicketComment:
        self.db.add(comment)
        return comment

    async def list_comments(
        self, ticket_id: uuid.UUID, include_internal: bool = True
    ) -> Sequence[TicketComment]:
        stmt = (
            select(TicketComment)
            .options(selectinload(TicketComment.author))
            .where(TicketComment.ticket_id == ticket_id)
        )
        if not include_internal:
            stmt = stmt.where(TicketComment.is_internal.is_(False))
        stmt = stmt.order_by(TicketComment.created_at.asc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

