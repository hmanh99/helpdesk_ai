import logging
from pathlib import Path
from typing import Optional
import uuid

from fastapi import HTTPException, UploadFile, status

from app.ai.chunking import chunk_text
from app.ai.extractors import extract_text_from_file
from app.ai.llm import LLMClient
from app.core.config import settings
from app.models.enums import ProcessingStatus
from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
from app.models.user import AppUser
from app.repo.category import CategoryRepository
from app.repo.knowledge import KnowledgeRepository
from app.schemas.knowledge import (
    KnowledgeChunkResponse,
    KnowledgeDocumentCreate,
    KnowledgeDocumentDetailResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
)
from app.security.policies import can_manage_knowledge

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Service quản lý tài liệu tri thức, xử lý tách đoạn (chunking), embedding và RAG."""

    def __init__(
        self,
        knowledge_repo: KnowledgeRepository,
        category_repo: CategoryRepository,
        llm_client: LLMClient,
    ) -> None:
        self.knowledge_repo = knowledge_repo
        self.category_repo = category_repo
        self.llm_client = llm_client

    def _to_response(self, doc: KnowledgeDocument) -> KnowledgeDocumentResponse:
        cat_name = doc.category.name if doc.category else None
        chunks_count = len(doc.chunks) if doc.chunks else 0
        return KnowledgeDocumentResponse(
            id=doc.id,
            category_id=doc.category_id,
            category_name=cat_name,
            title=doc.title,
            content=doc.content,
            source_url=doc.source_url,
            file_name=doc.file_name,
            mime_type=doc.mime_type,
            file_size=doc.file_size,
            processing_status=doc.processing_status,
            processing_error=doc.processing_error,
            is_published=doc.is_published,
            created_by=doc.created_by,
            chunk_count=chunks_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    def _to_detail_response(
        self, doc: KnowledgeDocument
    ) -> KnowledgeDocumentDetailResponse:
        base_resp = self._to_response(doc)
        chunk_items = [
            KnowledgeChunkResponse(
                id=c.id,
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
            )
            for c in (doc.chunks or [])
        ]
        return KnowledgeDocumentDetailResponse(
            **base_resp.model_dump(),
            chunks=chunk_items,
        )

    async def _embed_and_save_chunks(self, doc: KnowledgeDocument, text: str) -> None:
        # Xóa các chunk cũ nếu có
        await self.knowledge_repo.delete_chunks(doc.id)

        # Tách đoạn
        text_chunks = chunk_text(text)
        if not text_chunks:
            return

        # Gọi mô hình tạo embedding vector
        contents = [c.content for c in text_chunks]
        vectors = await self.llm_client.embed(contents, task_type="RETRIEVAL_DOCUMENT")

        # Lưu các chunk mới
        db_chunks = [
            KnowledgeChunk(
                document_id=doc.id,
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
                embedding=vec,
            )
            for c, vec in zip(text_chunks, vectors)
        ]
        await self.knowledge_repo.create_chunks(db_chunks)

    async def create_from_text(
        self, body: KnowledgeDocumentCreate, current_user: AppUser
    ) -> KnowledgeDocumentResponse:
        if not can_manage_knowledge(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) và Trưởng bộ phận (DEPT_MANAGER) mới có quyền tạo tài liệu tri thức",
            )

        if body.category_id is not None:
            cat = await self.category_repo.get_by_id(body.category_id)
            if cat is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục được chỉ định không tồn tại",
                )
            if not can_manage_knowledge(current_user, target_dept_id=cat.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trưởng bộ phận chỉ có quyền tạo tài liệu thuộc danh mục của bộ phận mình",
                )

        doc = KnowledgeDocument(
            title=body.title.strip(),
            category_id=body.category_id,
            content=body.content.strip(),
            source_url=body.source_url,
            processing_status=ProcessingStatus.READY,
            is_published=False,
            created_by=current_user.id,
        )
        await self.knowledge_repo.create(doc)
        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(doc)

        # Tách đoạn và embed
        await self._embed_and_save_chunks(doc, doc.content)
        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(doc)

        return self._to_response(doc)

    async def upload_file(
        self,
        file: UploadFile,
        title: str,
        category_id: Optional[uuid.UUID],
        current_user: AppUser,
        source_url: Optional[str] = None,
        is_published: bool = False,
    ) -> KnowledgeDocumentResponse:
        if not can_manage_knowledge(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) và Trưởng bộ phận (DEPT_MANAGER) mới có quyền tải lên tài liệu tri thức",
            )

        if category_id is not None:
            cat = await self.category_repo.get_by_id(category_id)
            if cat is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục được chỉ định không tồn tại",
                )
            if not can_manage_knowledge(current_user, target_dept_id=cat.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trưởng bộ phận chỉ có quyền tải lên tài liệu thuộc danh mục của bộ phận mình",
                )

        filename = file.filename or "uploaded_file"
        ext = Path(filename).suffix.lower()
        allowed_exts = {".txt", ".md", ".pdf", ".docx"}
        if ext not in allowed_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Định dạng {ext} không được hỗ trợ. Chỉ chấp nhận .txt, .md, .pdf, .docx",
            )

        content_bytes = await file.read()
        max_bytes = settings.KNOWLEDGE_MAX_FILE_MB * 1024 * 1024
        if len(content_bytes) > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dung lượng file vượt quá giới hạn cho phép ({settings.KNOWLEDGE_MAX_FILE_MB}MB)",
            )

        storage_dir = Path(settings.KNOWLEDGE_STORAGE_DIR)
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_uuid = uuid.uuid4()
        saved_path = storage_dir / f"{file_uuid}{ext}"
        saved_path.write_bytes(content_bytes)

        doc = KnowledgeDocument(
            id=file_uuid,
            title=title.strip() if title else filename,
            category_id=category_id,
            content="",  # Sẽ được trích xuất khi xử lý
            source_url=source_url,
            file_path=str(saved_path),
            file_name=filename,
            mime_type=file.content_type,
            file_size=len(content_bytes),
            processing_status=ProcessingStatus.PENDING,
            is_published=False,
            created_by=current_user.id,
        )
        await self.knowledge_repo.create(doc)
        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(doc)

        # Xử lý trích xuất và embedding trực tiếp
        await self.process_document(doc.id)
        await self.knowledge_repo.refresh(doc)

        if doc.processing_status == ProcessingStatus.FAILED:
            err_msg = doc.processing_error or "Trích xuất tài liệu thất bại"
            if saved_path.exists():
                try:
                    saved_path.unlink()
                except OSError:
                    pass
            await self.knowledge_repo.delete(doc)
            await self.knowledge_repo.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Lỗi khi xử lý tài liệu: {err_msg}",
            )

        if is_published and doc.processing_status == ProcessingStatus.READY:
            doc.is_published = True
            await self.knowledge_repo.commit()
            await self.knowledge_repo.refresh(doc)

        return self._to_response(doc)

    async def process_document(self, doc_id: uuid.UUID) -> None:
        doc = await self.knowledge_repo.get_by_id(doc_id)
        if doc is None or not doc.file_path:
            return

        doc.processing_status = ProcessingStatus.PROCESSING
        doc.processing_error = None
        await self.knowledge_repo.commit()

        try:
            extracted_text = extract_text_from_file(doc.file_path, doc.mime_type)
            doc.content = extracted_text
            await self._embed_and_save_chunks(doc, extracted_text)
            doc.processing_status = ProcessingStatus.READY
            await self.knowledge_repo.commit()
        except Exception as e:
            logger.exception("Lỗi khi xử lý tài liệu tri thức %s: %s", doc_id, e)
            doc.processing_status = ProcessingStatus.FAILED
            doc.processing_error = str(e)
            await self.knowledge_repo.commit()

    async def list_documents(
        self,
        category_id: Optional[uuid.UUID] = None,
        published_only: bool = False,
        status: Optional[ProcessingStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[KnowledgeDocumentResponse]:
        docs = await self.knowledge_repo.list_documents(
            category_id=category_id,
            published_only=published_only,
            status=status,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(d) for d in docs]

    async def get_document(
        self, doc_id: uuid.UUID
    ) -> KnowledgeDocumentDetailResponse:
        doc = await self.knowledge_repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu tri thức",
            )
        return self._to_detail_response(doc)

    async def get_document_chunks(
        self, doc_id: uuid.UUID
    ) -> list[KnowledgeChunkResponse]:
        doc = await self.knowledge_repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu tri thức",
            )
        chunks = await self.knowledge_repo.get_chunks_by_document_id(doc_id)
        return [
            KnowledgeChunkResponse(
                id=c.id,
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
            )
            for c in chunks
        ]

    async def update_document(
        self,
        doc_id: uuid.UUID,
        body: KnowledgeDocumentUpdate,
        current_user: AppUser,
    ) -> KnowledgeDocumentResponse:
        if not can_manage_knowledge(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) và Trưởng bộ phận (DEPT_MANAGER) mới có quyền chỉnh sửa tài liệu",
            )

        doc = await self.knowledge_repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu tri thức",
            )

        if doc.category and doc.category.department_id is not None:
            if not can_manage_knowledge(current_user, target_dept_id=doc.category.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trưởng bộ phận chỉ có quyền chỉnh sửa tài liệu thuộc bộ phận mình",
                )

        if body.category_id is not None:
            cat = await self.category_repo.get_by_id(body.category_id)
            if cat is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục được chỉ định không tồn tại",
                )
            if not can_manage_knowledge(current_user, target_dept_id=cat.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trưởng bộ phận chỉ có thể chuyển tài liệu sang danh mục thuộc bộ phận mình",
                )
            doc.category_id = body.category_id

        if body.title is not None:
            doc.title = body.title.strip()
        if body.source_url is not None:
            doc.source_url = body.source_url

        if body.content is not None and body.content.strip() != doc.content:
            doc.content = body.content.strip()
            await self._embed_and_save_chunks(doc, doc.content)

        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(doc)
        return self._to_response(doc)

    async def publish_document(
        self, doc_id: uuid.UUID, current_user: AppUser
    ) -> KnowledgeDocumentResponse:
        if not can_manage_knowledge(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) và Trưởng bộ phận (DEPT_MANAGER) mới có quyền xuất bản tài liệu",
            )

        doc = await self.knowledge_repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu tri thức",
            )

        if doc.category and doc.category.department_id is not None:
            if not can_manage_knowledge(current_user, target_dept_id=doc.category.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trưởng bộ phận chỉ có quyền xuất bản tài liệu thuộc bộ phận mình",
                )

        if doc.processing_status != ProcessingStatus.READY:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chỉ có thể xuất bản tài liệu ở trạng thái READY (Hiện tại: {doc.processing_status})",
            )

        doc.is_published = True
        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(doc)
        return self._to_response(doc)

    async def unpublish_document(
        self, doc_id: uuid.UUID, current_user: AppUser
    ) -> KnowledgeDocumentResponse:
        if not can_manage_knowledge(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) và Trưởng bộ phận (DEPT_MANAGER) mới có quyền gỡ xuất bản tài liệu",
            )

        doc = await self.knowledge_repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu tri thức",
            )

        if doc.category and doc.category.department_id is not None:
            if not can_manage_knowledge(current_user, target_dept_id=doc.category.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trưởng bộ phận chỉ có quyền gỡ xuất bản tài liệu thuộc bộ phận mình",
                )

        doc.is_published = False
        await self.knowledge_repo.commit()
        await self.knowledge_repo.refresh(doc)
        return self._to_response(doc)

    async def delete_document(
        self, doc_id: uuid.UUID, current_user: AppUser
    ) -> None:
        if not can_manage_knowledge(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) và Trưởng bộ phận (DEPT_MANAGER) mới có quyền xóa tài liệu",
            )

        doc = await self.knowledge_repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy tài liệu tri thức",
            )

        if doc.category and doc.category.department_id is not None:
            if not can_manage_knowledge(current_user, target_dept_id=doc.category.department_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Trưởng bộ phận chỉ có quyền xóa tài liệu thuộc bộ phận mình",
                )

        # Xoá file vật lý nếu có
        if doc.file_path:
            p = Path(doc.file_path)
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    logger.warning("Không thể xóa file lưu trữ: %s", doc.file_path)

        await self.knowledge_repo.delete(doc)
        await self.knowledge_repo.commit()

