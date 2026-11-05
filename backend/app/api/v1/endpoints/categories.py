from typing import Annotated, Optional
import uuid

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import (
    CategoryServiceDep,
    CurrentUserDep,
    require_roles,
)
from app.models.user import AppUser, UserRole
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate

router = APIRouter()

AdminOnlyDep = Annotated[AppUser, Depends(require_roles(UserRole.ADMIN))]


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    _: CurrentUserDep,
    category_service: CategoryServiceDep,
    department_id: Optional[uuid.UUID] = Query(None, description="Lọc theo phòng ban"),
    active_only: bool = Query(False, description="Chỉ lấy danh mục đang hoạt động"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> list[CategoryResponse]:
    return await category_service.list_categories(
        department_id=department_id,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )


@router.get("/{id}", response_model=CategoryResponse)
async def get_category(
    _: CurrentUserDep,
    id: uuid.UUID,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return await category_service.get_category(id)


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    current_admin: AdminOnlyDep,
    body: CategoryCreate,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return await category_service.create_category(body, current_admin)


@router.patch("/{id}", response_model=CategoryResponse)
async def update_category(
    current_admin: AdminOnlyDep,
    id: uuid.UUID,
    body: CategoryUpdate,
    category_service: CategoryServiceDep,
) -> CategoryResponse:
    return await category_service.update_category(id, body, current_admin)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    current_admin: AdminOnlyDep,
    id: uuid.UUID,
    category_service: CategoryServiceDep,
) -> None:
    await category_service.delete_category(id, current_admin)

