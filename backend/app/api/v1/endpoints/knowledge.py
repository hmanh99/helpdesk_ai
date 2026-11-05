from typing import Annotated, Optional
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status

from app.api.deps import CurrentUserDep, KnowledgeServiceDep, require_roles
from app.models.enums import ProcessingStatus
from app.models.user import AppUser, UserRole
from app.schemas.knowledge import (
    KnowledgeChunkResponse,
    KnowledgeDocumentCreate,
    KnowledgeDocumentDetailResponse,
    KnowledgeDocumentResponse,
    KnowledgeDocumentUpdate,
)

router = APIRouter()

AdminOrManagerDep = Annotated[
    AppUser, Depends(require_roles(UserRole.ADMIN, UserRole.DEPT_MANAGER))
]


@router.get("", response_model=list[KnowledgeDocumentResponse])
async def list_documents(
    _: AdminOrManagerDep,
    knowledge_service: KnowledgeServiceDep,
    category_id: Optional[uuid.UUID] = Query(None, description="Lọc theo danh mục"),
    published_only: bool = Query(False, description="Chỉ lấy tài liệu đã xuất bản"),
    status: Optional[ProcessingStatus] = Query(None, description="Lọc theo trạng thái xử lý"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> list[KnowledgeDocumentResponse]:
    return await knowledge_service.list_documents(
        category_id=category_id,
        published_only=published_only,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/{id}", response_model=KnowledgeDocumentDetailResponse)
async def get_document(
    _: AdminOrManagerDep,
    id: uuid.UUID,
    knowledge_service: KnowledgeServiceDep,
) -> KnowledgeDocumentDetailResponse:
    return await knowledge_service.get_document(id)


@router.get("/{id}/chunks", response_model=list[KnowledgeChunkResponse])
async def get_document_chunks(
    _: AdminOrManagerDep,
    id: uuid.UUID,
    knowledge_service: KnowledgeServiceDep,
) -> list[KnowledgeChunkResponse]:
    return await knowledge_service.get_document_chunks(id)


@router.post("", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    current_user: AdminOrManagerDep,
    body: KnowledgeDocumentCreate,
    knowledge_service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    return await knowledge_service.create_from_text(body, current_user)


@router.post("/upload", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    current_user: AdminOrManagerDep,
    knowledge_service: KnowledgeServiceDep,
    file: UploadFile = File(...),
    title: str = Form(""),
    category_id: Optional[uuid.UUID] = Form(None),
    source_url: Optional[str] = Form(None),
    is_published: bool = Form(False),
) -> KnowledgeDocumentResponse:
    return await knowledge_service.upload_file(
        file=file,
        title=title,
        category_id=category_id,
        current_user=current_user,
        source_url=source_url,
        is_published=is_published,
    )


@router.patch("/{id}", response_model=KnowledgeDocumentResponse)
async def update_document(
    current_user: AdminOrManagerDep,
    id: uuid.UUID,
    body: KnowledgeDocumentUpdate,
    knowledge_service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    return await knowledge_service.update_document(id, body, current_user)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    current_user: AdminOrManagerDep,
    id: uuid.UUID,
    knowledge_service: KnowledgeServiceDep,
) -> None:
    await knowledge_service.delete_document(id, current_user)


@router.post("/{id}/publish", response_model=KnowledgeDocumentResponse)
async def publish_document(
    current_user: AdminOrManagerDep,
    id: uuid.UUID,
    knowledge_service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    return await knowledge_service.publish_document(id, current_user)


@router.post("/{id}/unpublish", response_model=KnowledgeDocumentResponse)
async def unpublish_document(
    current_user: AdminOrManagerDep,
    id: uuid.UUID,
    knowledge_service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    return await knowledge_service.unpublish_document(id, current_user)


@router.post("/{id}/reprocess", response_model=KnowledgeDocumentResponse)
async def reprocess_document(
    current_user: AdminOrManagerDep,
    id: uuid.UUID,
    knowledge_service: KnowledgeServiceDep,
) -> KnowledgeDocumentResponse:
    await knowledge_service.process_document(id)
    return await knowledge_service.get_document(id)

