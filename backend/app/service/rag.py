import logging
from typing import Optional
import uuid

from app.ai.llm import LLMClient
from app.ai.prompts import RAG_SYSTEM_PROMPT
from app.ai.schemas import RagAnswerResult
from app.core.config import settings
from app.models.chat import ChatMessage
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.repo.knowledge import KnowledgeRepository

logger = logging.getLogger(__name__)


class RagService:
    """Service thực hiện tìm kiếm vector tương đồng (RAG) và sinh câu trả lời có trích dẫn."""

    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        llm_client: LLMClient,
    ) -> None:
        self.knowledge_repo = knowledge_repo
        self.llm_client = llm_client

    async def search_chunks(
        self,
        query: str,
        category_id: Optional[uuid.UUID] = None,
        top_k: int = 5,
        min_score: float = 0.55,
    ) -> list[tuple[KnowledgeChunk, KnowledgeDocument, float]]:
        # Tạo vector truy vấn
        vectors = await self.llm_client.embed([query], task_type="RETRIEVAL_QUERY")
        if not vectors:
            return []
        query_vec = vectors[0]

        # Tìm kiếm có ưu tiên theo category nếu có
        matches = await self.knowledge_repo.search_similar_chunks(
            query_vector=query_vec,
            top_k=top_k,
            category_id=category_id,
            min_score=min_score,
        )

        # Nếu lọc theo category không thấy kết quả, mở rộng tìm kiếm toàn hệ thống
        if not matches and category_id is not None:
            matches = await self.knowledge_repo.search_similar_chunks(
                query_vector=query_vec,
                top_k=top_k,
                category_id=None,
                min_score=min_score,
            )

        return matches

    async def answer(
        self,
        question: str,
        history: list[ChatMessage],
        category_id: Optional[uuid.UUID] = None,
    ) -> tuple[str, list[tuple[KnowledgeDocument, float]], bool, float]:
        """Trả lời câu hỏi từ tri thức RAG.
        Trả về tuple: (câu_trả_lời, danh_sách_nguồn_đã_dùng, can_resolve, điểm_tin_cậy_cao_nhất)
        """
        matches = await self.search_chunks(
            query=question,
            category_id=category_id,
            top_k=settings.RAG_TOP_K,
            min_score=settings.RAG_MIN_SCORE,
        )

        # Nếu không có tài liệu nào đạt ngưỡng tin cậy, không gọi LLM để bịa đặt
        if not matches:
            fallback_answer = (
                "Hiện tại hệ thống chưa tìm thấy tài liệu hướng dẫn cụ thể cho vấn đề này. "
                "Bạn có muốn tôi tạo phiếu hỗ trợ (Ticket) để chuyển yêu cầu đến phòng ban phụ trách không?"
            )
            return fallback_answer, [], False, 0.0

        top_score = matches[0][2]

        # Chuẩn bị context các đoạn tài liệu
        context_lines: list[str] = []
        for idx, (chunk, doc, score) in enumerate(matches, start=1):
            context_lines.append(f"[{idx}] (Tài liệu: {doc.title})\n{chunk.content}")
        context_chunks = "\n\n".join(context_lines)

        prompt = f"""Câu hỏi của người dùng:
{question}

Hãy dựa vào các đoạn tài liệu sau để trả lời:
{context_chunks}
"""

        try:
            rag_result = await self.llm_client.generate_json(
                prompt=prompt,
                response_schema=RagAnswerResult,
                system_instruction=RAG_SYSTEM_PROMPT.format(context_chunks=context_chunks),
            )
        except Exception as e:
            logger.exception("Lỗi khi gọi LLM sinh câu trả lời RAG: %s", e)
            # Fallback nếu LLM gặp sự cố
            rag_result = RagAnswerResult(
                answer=f"Hệ thống tìm thấy tài liệu liên quan nhưng gặp sự cố khi tổng hợp. Vui lòng tham khảo tài liệu: {matches[0][1].title}",
                used_chunk_indices=[1],
                can_resolve=True,
            )

        # Gom nhóm tài liệu nguồn đã dùng (lấy điểm cao nhất cho mỗi tài liệu)
        used_indices = set(rag_result.used_chunk_indices) if rag_result.used_chunk_indices else {1}
        doc_map: dict[uuid.UUID, tuple[KnowledgeDocument, float]] = {}

        for idx, (_, doc, score) in enumerate(matches, start=1):
            if idx in used_indices or len(used_indices) == 0:
                if doc.id not in doc_map or score > doc_map[doc.id][1]:
                    doc_map[doc.id] = (doc, score)

        # Nếu không có nguồn nào khớp index, lấy ít nhất tài liệu top 1
        if not doc_map and matches:
            doc_map[matches[0][1].id] = (matches[0][1], matches[0][2])

        return (
            rag_result.answer,
            list(doc_map.values()),
            rag_result.can_resolve,
            top_score,
        )

