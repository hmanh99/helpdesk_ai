from typing import Optional, Sequence
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatSession, MessageSource
from app.repo.base import BaseRepository


class ChatRepository(BaseRepository):
    """Repository quản lý cơ sở dữ liệu cho ChatSession và ChatMessage."""

    async def get_session_by_id(self, session_id: uuid.UUID) -> Optional[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .options(
                selectinload(ChatSession.messages).selectinload(ChatMessage.sources).selectinload(MessageSource.knowledge_document),
                selectinload(ChatSession.ticket),
            )
            .where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions_by_user(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> Sequence[ChatSession]:
        stmt = (
            select(ChatSession)
            .options(
                selectinload(ChatSession.messages),
                selectinload(ChatSession.ticket),
            )
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def list_all_sessions(
        self, skip: int = 0, limit: int = 50
    ) -> Sequence[ChatSession]:
        stmt = (
            select(ChatSession)
            .options(
                selectinload(ChatSession.messages),
                selectinload(ChatSession.ticket),
            )
            .order_by(ChatSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_session(self, session: ChatSession) -> ChatSession:
        self.db.add(session)
        return session

    async def add_message(self, message: ChatMessage) -> ChatMessage:
        self.db.add(message)
        return message

    async def add_sources(self, sources: list[MessageSource]) -> None:
        self.db.add_all(sources)

