from typing import Optional, Sequence
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from app.models.enums import ProcessingStatus
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.repo.base import BaseRepository


class KnowledgeRepository(BaseRepository):
    """Repository quản lý cơ sở dữ liệu cho tài liệu và vector chunk tri thức."""

    async def get_by_id(self, doc_id: uuid.UUID) -> Optional[KnowledgeDocument]:
        result = await self.db.execute(
            select(KnowledgeDocument)
            .options(selectinload(KnowledgeDocument.chunks))
            .where(KnowledgeDocument.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def list_documents(
        self,
        category_id: Optional[uuid.UUID] = None,
        published_only: bool = False,
        status: Optional[ProcessingStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[KnowledgeDocument]:
        stmt = select(KnowledgeDocument).options(selectinload(KnowledgeDocument.chunks))
        if category_id is not None:
            stmt = stmt.where(KnowledgeDocument.category_id == category_id)
        if published_only:
            stmt = stmt.where(KnowledgeDocument.is_published.is_(True))
        if status is not None:
            stmt = stmt.where(KnowledgeDocument.processing_status == status)
        stmt = stmt.order_by(KnowledgeDocument.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, doc: KnowledgeDocument) -> KnowledgeDocument:
        self.db.add(doc)
        return doc

    async def delete(self, doc: KnowledgeDocument) -> None:
        await self.db.delete(doc)

    async def delete_chunks(self, document_id: uuid.UUID) -> None:
        await self.db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id)
        )

    async def create_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        self.db.add_all(chunks)

    async def get_chunks_by_document_id(
        self, document_id: uuid.UUID
    ) -> Sequence[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunk)
            .where(KnowledgeChunk.document_id == document_id)
            .order_by(KnowledgeChunk.chunk_index.asc())
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def search_similar_chunks(
        self,
        query_vector: list[float],
        top_k: int = 5,
        category_id: Optional[uuid.UUID] = None,
        min_score: float = 0.55,
    ) -> list[tuple[KnowledgeChunk, KnowledgeDocument, float]]:
        """Tìm kiếm vector tương đồng cosine trên các chunk thuộc tài liệu đã published."""
        distance_col = KnowledgeChunk.embedding.cosine_distance(query_vector)
        score_col = (1.0 - distance_col).label("score")

        stmt = (
            select(KnowledgeChunk, KnowledgeDocument, score_col)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .where(KnowledgeDocument.is_published.is_(True))
            .where(KnowledgeDocument.processing_status == ProcessingStatus.READY)
        )

        if category_id is not None:
            stmt = stmt.where(KnowledgeDocument.category_id == category_id)

        stmt = stmt.order_by(distance_col).limit(top_k)
        result = await self.db.execute(stmt)
        rows = result.all()

        # Lọc theo min_score
        matches: list[tuple[KnowledgeChunk, KnowledgeDocument, float]] = []
        for chunk, doc, score in rows:
            sc_val = float(score) if score is not None else 0.0
            if sc_val >= min_score:
                matches.append((chunk, doc, sc_val))

        return matches

