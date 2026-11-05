import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    department_id: uuid.UUID
    description: Optional[str] = None
    sla_response_minutes: int = Field(default=60, ge=1)
    sla_resolve_minutes: int = Field(default=1440, ge=1)
    is_active: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    department_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    sla_response_minutes: Optional[int] = Field(None, ge=1)
    sla_resolve_minutes: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class CategoryResponse(CategoryBase):
    id: uuid.UUID
    department_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

