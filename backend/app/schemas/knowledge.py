import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProcessingStatus


class KnowledgeDocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    category_id: Optional[uuid.UUID] = None
    source_url: Optional[str] = Field(None, max_length=500)


class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    content: str = Field(..., min_length=1)


class KnowledgeDocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category_id: Optional[uuid.UUID] = None
    content: Optional[str] = Field(None, min_length=1)
    source_url: Optional[str] = Field(None, max_length=500)


class KnowledgeChunkResponse(BaseModel):
    id: uuid.UUID
    chunk_index: int
    content: str
    token_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentResponse(KnowledgeDocumentBase):
    id: uuid.UUID
    category_name: Optional[str] = None
    content: str
    file_name: Optional[str] = None
    mime_type: Optional[str] = None
    file_size: Optional[int] = None
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    is_published: bool
    created_by: Optional[uuid.UUID] = None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentDetailResponse(KnowledgeDocumentResponse):
    chunks: list[KnowledgeChunkResponse] = []

