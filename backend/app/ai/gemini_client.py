import logging
import math
from typing import Optional, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.ai.llm import LLMClient
from app.core.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def is_transient_error(e: BaseException) -> bool:
    if isinstance(e, (genai.errors.ServerError, TimeoutError)):
        return True
    if isinstance(e, genai.errors.ClientError) and getattr(e, "code", None) == 429:
        return True
    err_str = str(e)
    return "429" in err_str or "RESOURCE_EXHAUSTED" in err_str or "503" in err_str


def normalize_l2(vec: list[float]) -> list[float]:
    """Chuẩn hoá vector về độ dài L2 = 1.0 phục vụ tìm kiếm Cosine Similarity."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


class GeminiClient(LLMClient):
    """Triển khai LLMClient sử dụng Google Gemini SDK chính thức (google-genai)."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.GOOGLE_API_KEY
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY chưa được cấu hình. GeminiClient sẽ không thể gọi API thực tế.")
        self.client = genai.Client(api_key=self.api_key)
        self.chat_model = settings.GEMINI_CHAT_MODEL
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL
        self.embedding_dim = settings.EMBEDDING_DIM

    @retry(
        retry=retry_if_exception(is_transient_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        reraise=True,
    )
    async def generate_json(
        self,
        prompt: str,
        response_schema: type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.1,
            system_instruction=system_instruction,
        )
        response = await self.client.aio.models.generate_content(
            model=self.chat_model,
            contents=prompt,
            config=config,
        )
        if not response.text:
            raise ValueError("Mô hình không trả về nội dung phản hồi")
        return response_schema.model_validate_json(response.text)

    @retry(
        retry=retry_if_exception(is_transient_error),
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        reraise=True,
    )
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        config = types.GenerateContentConfig(
            temperature=0.3,
            system_instruction=system_instruction,
        )
        response = await self.client.aio.models.generate_content(
            model=self.chat_model,
            contents=prompt,
            config=config,
        )
        return (response.text or "").strip()

    async def embed(
        self,
        texts: list[str],
        task_type: str = "RETRIEVAL_DOCUMENT",
    ) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float]] = []
        batch_size = 50

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            config = types.EmbedContentConfig(
                output_dimensionality=self.embedding_dim,
                task_type=task_type,
            )
            response = await self.client.aio.models.embed_content(
                model=self.embedding_model,
                contents=batch,
                config=config,
            )
            for emb in response.embeddings:
                normalized = normalize_l2(list(emb.values))
                results.append(normalized)

        return results
