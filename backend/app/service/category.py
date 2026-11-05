import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.models.category import Category
from app.models.user import AppUser
from app.repo.category import CategoryRepository
from app.repo.department import DepartmentRepository
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.security.policies import can_manage_category


class CategoryService:
    """Service xử lý nghiệp vụ quản lý danh mục (Category)."""

    def __init__(
        self,
        category_repo: CategoryRepository,
        department_repo: DepartmentRepository,
    ) -> None:
        self.category_repo = category_repo
        self.dept_repo = department_repo

    def _to_response(self, category: Category) -> CategoryResponse:
        dept_name = category.department.name if category.department else None
        return CategoryResponse(
            id=category.id,
            name=category.name,
            department_id=category.department_id,
            department_name=dept_name,
            description=category.description,
            sla_response_minutes=category.sla_response_minutes,
            sla_resolve_minutes=category.sla_resolve_minutes,
            is_active=category.is_active,
            created_at=category.created_at,
            updated_at=category.updated_at,
        )

    async def create_category(
        self, body: CategoryCreate, current_user: AppUser
    ) -> CategoryResponse:
        if not can_manage_category(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) mới có quyền tạo danh mục",
            )

        dept = await self.dept_repo.get_by_id(body.department_id)
        if dept is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Phòng ban được chỉ định không tồn tại",
            )

        existing = await self.category_repo.get_by_name(body.name)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục với tên này đã tồn tại",
            )

        category = Category(
            name=body.name.strip(),
            department_id=body.department_id,
            description=body.description,
            sla_response_minutes=body.sla_response_minutes,
            sla_resolve_minutes=body.sla_resolve_minutes,
            is_active=body.is_active,
        )
        await self.category_repo.create(category)
        try:
            await self.category_repo.commit()
        except IntegrityError:
            await self.category_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục với tên này đã tồn tại",
            )

        await self.category_repo.refresh(category)
        return self._to_response(category)

    async def list_categories(
        self,
        department_id: Optional[uuid.UUID] = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CategoryResponse]:
        categories = await self.category_repo.list_categories(
            department_id=department_id,
            active_only=active_only,
            skip=skip,
            limit=limit,
        )
        return [self._to_response(c) for c in categories]

    async def get_category(self, category_id: uuid.UUID) -> CategoryResponse:
        category = await self.category_repo.get_by_id(category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy danh mục",
            )
        return self._to_response(category)

    async def update_category(
        self,
        category_id: uuid.UUID,
        body: CategoryUpdate,
        current_user: AppUser,
    ) -> CategoryResponse:
        if not can_manage_category(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) mới có quyền cập nhật danh mục",
            )

        category = await self.category_repo.get_by_id(category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy danh mục",
            )

        if body.department_id is not None:
            dept = await self.dept_repo.get_by_id(body.department_id)
            if dept is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Phòng ban được chỉ định không tồn tại",
                )
            category.department_id = body.department_id

        if body.name is not None and body.name.strip() != category.name:
            existing = await self.category_repo.get_by_name(body.name)
            if existing is not None and existing.id != category.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tên danh mục này đã được sử dụng",
                )
            category.name = body.name.strip()

        if body.description is not None:
            category.description = body.description
        if body.sla_response_minutes is not None:
            category.sla_response_minutes = body.sla_response_minutes
        if body.sla_resolve_minutes is not None:
            category.sla_resolve_minutes = body.sla_resolve_minutes
        if body.is_active is not None:
            category.is_active = body.is_active

        try:
            await self.category_repo.commit()
        except IntegrityError:
            await self.category_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cập nhật danh mục thất bại do trùng lặp dữ liệu",
            )

        await self.category_repo.refresh(category)
        return self._to_response(category)

    async def delete_category(
        self,
        category_id: uuid.UUID,
        current_user: AppUser,
    ) -> None:
        if not can_manage_category(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Chỉ Quản trị viên (ADMIN) mới có quyền xóa danh mục",
            )

        category = await self.category_repo.get_by_id(category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy danh mục",
            )

        await self.category_repo.delete(category)
        try:
            await self.category_repo.commit()
        except IntegrityError:
            await self.category_repo.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể xóa danh mục đang có tài liệu hoặc ticket liên kết",
            )

