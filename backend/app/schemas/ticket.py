import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Channel, Priority, TicketStatus


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề yêu cầu hỗ trợ")
    description: str = Field(..., min_length=1, description="Chi tiết nội dung yêu cầu hoặc sự cố")
    category_id: Optional[uuid.UUID] = Field(None, description="Danh mục yêu cầu nếu người dùng tự chọn")
    priority: Priority = Field(default=Priority.MEDIUM, description="Mức độ ưu tiên")
    channel: Channel = Field(default=Channel.WEB_FORM, description="Kênh tạo ticket")
    chat_session_id: Optional[uuid.UUID] = Field(None, description="ID phiên chat liên quan nếu tạo từ chatbot")


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    category_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    assignee_id: Optional[uuid.UUID] = None
    priority: Optional[Priority] = None
    status: Optional[TicketStatus] = None


class TicketAcceptRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=500, description="Ghi chú khi tiếp nhận phiếu hỗ trợ")


class TicketAssignRequest(BaseModel):
    assignee_id: uuid.UUID = Field(..., description="ID của kỹ thuật viên được phân công")
    note: Optional[str] = Field(None, max_length=500, description="Ghi chú phân công công việc")


class TicketStatusUpdateRequest(BaseModel):
    status: TicketStatus = Field(..., description="Trạng thái mới của ticket")
    note: Optional[str] = Field(None, max_length=1000, description="Ghi chú lý do thay đổi trạng thái hoặc hướng dẫn giải quyết")


class TicketCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Nội dung phản hồi hoặc hướng dẫn xử lý")
    is_internal: bool = Field(default=False, description="Ghi chú nội bộ dành riêng cho cán bộ phòng ban")


class TicketCommentResponse(BaseModel):
    id: uuid.UUID
    ticket_id: uuid.UUID
    author_id: uuid.UUID
    author_name: Optional[str] = None
    author_role: Optional[str] = None
    content: str
    is_internal: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketHistoryResponse(BaseModel):
    id: uuid.UUID
    old_status: Optional[str] = None
    new_status: str
    note: Optional[str] = None
    changed_by: Optional[uuid.UUID] = None
    changed_by_name: Optional[str] = None
    changed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AIClassificationResponse(BaseModel):
    id: uuid.UUID
    predicted_category_id: Optional[uuid.UUID] = None
    predicted_category_name: Optional[str] = None
    suggested_priority: Optional[Priority] = None
    confidence_score: float
    model_version: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    requester_id: uuid.UUID
    requester_name: Optional[str] = None
    assignee_id: Optional[uuid.UUID] = None
    assignee_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    chat_session_id: Optional[uuid.UUID] = None
    priority: Priority
    status: TicketStatus
    channel: Channel
    created_at: datetime
    resolved_at: Optional[datetime] = None
    histories: list[TicketHistoryResponse] = []
    comments: list[TicketCommentResponse] = []
    classification: Optional[AIClassificationResponse] = None

    model_config = ConfigDict(from_attributes=True)

