import logging
from typing import Optional, Sequence
import uuid

from app.ai.llm import LLMClient
from app.ai.prompts import (
    INTENT_SYSTEM_PROMPT,
    TICKET_CLASSIFICATION_PROMPT,
    TICKET_DRAFT_PROMPT,
)
from app.ai.schemas import ClassificationResult, IntentResult, TicketDraft
from app.core.config import settings
from app.models.category import Category
from app.models.chat import ChatMessage
from app.models.enums import Intent, Priority
from app.models.ticket import AIClassification, Ticket

logger = logging.getLogger(__name__)


def format_categories_prompt(categories: Sequence[Category]) -> str:
    lines = []
    for c in categories:
        if c.is_active:
            desc = f": {c.description}" if c.description else ""
            lines.append(f"- ID: {c.id} | Tên: {c.name}{desc}")
    return "\n".join(lines) if lines else "(Không có danh mục nào)"


class IntentClassifier:
    """Bộ phân loại ý định (Intent) của người dùng từ câu hỏi và lịch sử trao đổi."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def classify(
        self,
        message: str,
        history: list[ChatMessage],
        categories: Sequence[Category],
    ) -> IntentResult:
        categories_text = format_categories_prompt(categories)
        system_instruction = INTENT_SYSTEM_PROMPT.format(categories_text=categories_text)

        # Chuẩn bị lịch sử gần nhất (3 lượt gần nhất)
        recent_history = history[-6:] if len(history) > 6 else history
        hist_lines = []
        for h in recent_history:
            sender_label = "Người dùng" if h.sender.value == "USER" else "Trợ lý"
            hist_lines.append(f"{sender_label}: {h.content}")
        history_text = "\n".join(hist_lines) if hist_lines else "(Cuộc hội thoại mới)"

        prompt = f"""Lịch sử hội thoại trước đó:
{history_text}

Tin nhắn mới nhất của người dùng:
{message}
"""
        try:
            result = await self.llm_client.generate_json(
                prompt=prompt,
                response_schema=IntentResult,
                system_instruction=system_instruction,
            )
        except Exception as e:
            logger.exception("Lỗi khi phân loại ý định: %s", e)
            return IntentResult(
                intent=Intent.KB_QUESTION,
                confidence=0.5,
                reason="Lỗi phân loại, mặc định tìm kiếm tài liệu",
            )

        # Kiểm tra tính hợp lệ của category_id
        if result.category_id:
            valid_ids = {str(c.id) for c in categories}
            if result.category_id not in valid_ids:
                result.category_id = None

        return result


class ClassifierService:
    """Service phân loại Ticket bằng AI (dự đoán danh mục và mức độ ưu tiên)."""

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def classify_ticket(
        self,
        ticket: Ticket,
        categories: Sequence[Category],
    ) -> ClassificationResult:
        categories_text = format_categories_prompt(categories)
        prompt = TICKET_CLASSIFICATION_PROMPT.format(
            title=ticket.title,
            description=ticket.description,
            categories_text=categories_text,
        )

        try:
            result = await self.llm_client.generate_json(
                prompt=prompt,
                response_schema=ClassificationResult,
            )
        except Exception as e:
            logger.exception("Lỗi khi phân loại Ticket bằng AI: %s", e)
            return ClassificationResult(
                category_id=None,
                priority=ticket.priority,
                confidence=0.0,
                reason=f"AI classification failed: {e}",
            )

        if result.category_id:
            valid_ids = {str(c.id) for c in categories}
            if result.category_id not in valid_ids:
                result.category_id = None

        return result

    async def generate_ticket_draft(
        self,
        history: list[ChatMessage],
        categories: Sequence[Category],
    ) -> TicketDraft:
        """Tóm tắt lịch sử hội thoại thành bản nháp Ticket để người dùng kiểm tra."""
        categories_text = format_categories_prompt(categories)
        hist_lines = []
        for h in history:
            sender_label = "Người dùng" if h.sender.value == "USER" else "Trợ lý"
            hist_lines.append(f"{sender_label}: {h.content}")
        history_text = "\n".join(hist_lines)

        prompt = TICKET_DRAFT_PROMPT.format(
            chat_history=history_text,
            categories_text=categories_text,
        )

        try:
            draft = await self.llm_client.generate_json(
                prompt=prompt,
                response_schema=TicketDraft,
            )
        except Exception as e:
            logger.exception("Lỗi khi tạo bản nháp Ticket: %s", e)
            # Fallback tạo draft cơ bản từ câu hỏi gần nhất của user
            last_user_msg = next((h.content for h in reversed(history) if h.sender.value == "USER"), "Yêu cầu hỗ trợ")
            draft = TicketDraft(
                title=last_user_msg[:80],
                description=history_text,
                priority=Priority.MEDIUM,
                reason="Tự động tạo từ hội thoại",
            )

        if draft.category_id:
            valid_ids = {str(c.id) for c in categories}
            if draft.category_id not in valid_ids:
                draft.category_id = None

        return draft


class RoutingService:
    """Service tự động định tuyến Ticket tới phòng ban tương ứng."""

    @staticmethod
    def route_ticket(
        ticket: Ticket,
        classification: AIClassification,
        categories: Sequence[Category],
        confidence_threshold: float = 0.6,
    ) -> bool:
        """Gán department_id và category_id nếu độ tin cậy đạt ngưỡng.
        Trả về True nếu tự động định tuyến thành công.
        """
        if classification.confidence_score < confidence_threshold:
            return False

        if not classification.predicted_category_id:
            return False

        # Tìm category trong danh sách
        cat = next((c for c in categories if c.id == classification.predicted_category_id), None)
        if cat is None:
            return False

        ticket.category_id = cat.id
        ticket.department_id = cat.department_id
        if classification.suggested_priority:
            ticket.priority = classification.suggested_priority
        return True

