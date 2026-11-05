import hashlib
import math
from typing import Any, Optional, TypeVar

from pydantic import BaseModel

from app.ai.llm import LLMClient
from app.ai.schemas import (
    ClassificationResult,
    IntentResult,
    RagAnswerResult,
    TicketDraft,
)
from app.models.enums import Intent, Priority

T = TypeVar("T", bound=BaseModel)


class FakeLLMClient(LLMClient):
    """Giả lập LLMClient dùng cho unit tests (hoàn toàn chạy offline, không gọi mạng)."""

    def __init__(self, embedding_dim: int = 768) -> None:
        self.embedding_dim = embedding_dim
        self.preset_json_responses: list[Any] = []
        self.preset_text_responses: list[str] = []
        self.calls: list[dict[str, Any]] = []

    def queue_json(self, response: Any) -> None:
        self.preset_json_responses.append(response)

    def queue_text(self, response: str) -> None:
        self.preset_text_responses.append(response)

    def _deterministic_vector(self, text: str) -> list[float]:
        # Sinh vector 768 chiều từ hash của text, đảm bảo chuẩn hoá L2
        h = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [100.0 + (float(h[i % len(h)]) / 255.0) * 10.0 for i in range(self.embedding_dim)]
        norm = math.sqrt(sum(x * x for x in vec))
        return [x / norm for x in vec] if norm > 0 else vec

    async def embed(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        self.calls.append({"method": "embed", "texts": texts, "task_type": task_type})
        return [self._deterministic_vector(t) for t in texts]

    async def generate_json(
        self,
        prompt: str,
        response_schema: type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        self.calls.append({
            "method": "generate_json",
            "prompt": prompt,
            "schema": response_schema.__name__,
            "system": system_instruction,
        })
        if self.preset_json_responses:
            val = self.preset_json_responses.pop(0)
            if isinstance(val, response_schema):
                return val
            if isinstance(val, dict):
                return response_schema.model_validate(val)
            if isinstance(val, str):
                return response_schema.model_validate_json(val)

        # Mặc định theo schema nếu không có preset
        if response_schema is IntentResult:
            return response_schema(
                intent=Intent.KB_QUESTION,
                category_id=None,
                confidence=0.9,
                reason="Fake classifier default",
            )  # type: ignore[return-value]
        if response_schema is RagAnswerResult:
            return response_schema(
                answer="Đây là câu trả lời thử nghiệm từ tài liệu [1].",
                used_chunk_indices=[1],
                can_resolve=True,
            )  # type: ignore[return-value]
        if response_schema is TicketDraft:
            return response_schema(
                title="Sự cố kiểm thử",
                description="Mô tả sự cố kiểm thử chi tiết",
                priority=Priority.MEDIUM,
                reason="Lý do kiểm thử",
            )  # type: ignore[return-value]
        if response_schema is ClassificationResult:
            return response_schema(
                category_id=None,
                priority=Priority.MEDIUM,
                confidence=0.85,
                reason="Phân loại kiểm thử",
            )  # type: ignore[return-value]

        return response_schema.model_validate({})

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        self.calls.append({"method": "generate_text", "prompt": prompt})
        if self.preset_text_responses:
            return self.preset_text_responses.pop(0)
        return "Phản hồi giả lập từ LLM."
