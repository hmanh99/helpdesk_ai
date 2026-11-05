from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import Intent, Priority


class IntentResult(BaseModel):
    intent: Intent
    category_id: Optional[str] = Field(
        default=None,
        description="ID của category phù hợp nhất nếu xác định được (hoặc null)",
    )
    priority: Optional[Priority] = Field(
        default=None,
        description="Mức độ ưu tiên đề xuất nếu là yêu cầu cần phòng ban",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Độ tin cậy từ 0.0 đến 1.0",
    )
    reason: str = Field(
        default="",
        description="Lý do phân loại ngắn gọn",
    )
    clarification_question: Optional[str] = Field(
        default=None,
        description="Câu hỏi làm rõ khi ý định chưa rõ ràng (UNCLEAR)",
    )


class TicketDraft(BaseModel):
    title: str = Field(..., description="Tiêu đề ngắn gọn mô tả sự cố hoặc yêu cầu")
    description: str = Field(..., description="Mô tả chi tiết sự cố, bối cảnh, lỗi gặp phải")
    category_id: Optional[str] = Field(
        default=None,
        description="ID danh mục sự cố phù hợp nếu xác định được",
    )
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Mức độ ưu tiên",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Tóm tắt lý do hoặc hướng xử lý sơ bộ",
    )


class ClassificationResult(BaseModel):
    category_id: Optional[str] = Field(
        default=None,
        description="ID category được dự đoán",
    )
    priority: Priority = Field(
        default=Priority.MEDIUM,
        description="Mức độ ưu tiên đề xuất",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của dự đoán",
    )
    reason: str = Field(
        default="",
        description="Giải thích ngắn gọn cho phân loại này",
    )


class RagAnswerResult(BaseModel):
    answer: str = Field(
        ...,
        description="Câu trả lời đầy đủ, thân thiện, trích dẫn nguồn dạng [1], [2] nếu có",
    )
    used_chunk_indices: list[int] = Field(
        default_factory=list,
        description="Danh sách chỉ số [1], [2]... của các đoạn tài liệu thực sự được sử dụng",
    )
    can_resolve: bool = Field(
        default=True,
        description="True nếu tài liệu đủ thông tin giải quyết, False nếu thông tin còn thiếu",
    )

