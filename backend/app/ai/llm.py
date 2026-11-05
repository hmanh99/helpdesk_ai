from typing import Optional, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    """Protocol giao tiếp trừu tượng với các mô hình LLM và Embedding."""

    async def generate_json(
        self,
        prompt: str,
        response_schema: type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        """Sinh đầu ra có cấu trúc (structured output) theo schema Pydantic."""
        ...

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Sinh văn bản tự do."""
        ...

    async def embed(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        """Tạo vector embedding cho danh sách văn bản (đã chuẩn hoá L2, độ dài 768)."""
        ...

