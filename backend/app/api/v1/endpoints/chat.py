from typing import Optional
import uuid

from fastapi import APIRouter, Query, status

from app.api.deps import ChatServiceDep, CurrentUserDep
from app.schemas.chat import (
    ChatMessageResponse,
    ChatReplyResponse,
    ChatSessionDetailResponse,
    ChatSessionResponse,
    FeedbackRequest,
    SendMessageRequest,
)
from app.schemas.ticket import TicketCreate, TicketResponse

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    current_user: CurrentUserDep,
    chat_service: ChatServiceDep,
) -> ChatSessionResponse:
    """Tạo mới một phiên hội thoại chat."""
    return await chat_service.create_session(current_user)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_sessions(
    current_user: CurrentUserDep,
    chat_service: ChatServiceDep,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[ChatSessionResponse]:
    """Lấy danh sách các phiên chat của người dùng hiện tại (Admin xem được tất cả)."""
    return await chat_service.list_sessions(current_user, skip=skip, limit=limit)


@router.get("/sessions/{id}", response_model=ChatSessionDetailResponse)
async def get_session(
    current_user: CurrentUserDep,
    id: uuid.UUID,
    chat_service: ChatServiceDep,
) -> ChatSessionDetailResponse:
    """Xem chi tiết phiên chat kèm toàn bộ lịch sử tin nhắn và nguồn trích dẫn."""
    return await chat_service.get_session(id, current_user)


@router.post("/sessions/{id}/messages", response_model=ChatReplyResponse)
async def send_message(
    current_user: CurrentUserDep,
    id: uuid.UUID,
    body: SendMessageRequest,
    chat_service: ChatServiceDep,
) -> ChatReplyResponse:
    """Gửi câu hỏi trong phiên chat: Hệ thống tự động phân loại ý định, tra cứu RAG hoặc đề xuất bản nháp Ticket."""
    return await chat_service.send_message(id, current_user, body.content)


@router.post("/sessions/{id}/feedback", response_model=ChatReplyResponse)
async def submit_feedback(
    current_user: CurrentUserDep,
    id: uuid.UUID,
    body: FeedbackRequest,
    chat_service: ChatServiceDep,
) -> ChatReplyResponse:
    """Gửi phản hồi về câu trả lời của Chatbot (Đã giải quyết / Chưa giải quyết). Nếu chưa, hệ thống tự động soạn nháp Ticket."""
    return await chat_service.submit_feedback(id, current_user, body.resolved)


@router.post("/sessions/{id}/ticket", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def confirm_ticket(
    current_user: CurrentUserDep,
    id: uuid.UUID,
    chat_service: ChatServiceDep,
    body: Optional[TicketCreate] = None,
) -> TicketResponse:
    """Người dùng xác nhận tạo Phiếu hỗ trợ (Ticket) từ phiên chat (có thể gửi kèm chỉnh sửa tiêu đề, mô tả, danh mục)."""
    return await chat_service.confirm_ticket_from_session(id, current_user, body)

