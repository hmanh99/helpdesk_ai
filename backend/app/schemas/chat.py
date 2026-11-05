import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.ai.schemas import TicketDraft
from app.models.enums import Intent, MessageSender


class MessageSourceRequestResponse(BaseModel):
    knowledge_document_id: uuid.UUID
    title: str
    source_url: Optional[str] = None
    relevance_score: float

    model_config = ConfigDict(from_attributes=True)


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    sender: MessageSender
    content: str
    intent: Optional[Intent] = None
    confidence_score: Optional[float] = None
    ticket_draft: Optional[dict[str, Any]] = None
    sources: list[MessageSourceRequestResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_resolved_by_bot: Optional[bool] = None
    message_count: int = 0
    ticket_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class ChatSessionDetailResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatMessageResponse]


class SendMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Nội dung câu hỏi của người dùng")


class ChatReplyResponse(BaseModel):
    message: ChatMessageResponse
    suggest_ticket: bool = False
    ticket_draft: Optional[TicketDraft] = None


class FeedbackRequest(BaseModel):
    resolved: bool = Field(..., description="True nếu bot đã giải quyết được vấn đề, False nếu chưa")

