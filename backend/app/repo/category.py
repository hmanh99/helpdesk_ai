from typing import Optional, Sequence
import uuid

from sqlalchemy import select

from app.models.category import Category
from app.repo.base import BaseRepository


class CategoryRepository(BaseRepository):
    """Repository quản lý các thao tác cơ sở dữ liệu đối với bảng Category."""

    async def get_by_id(self, category_id: uuid.UUID) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(Category.id == category_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(Category.name == name.strip())
        )
        return result.scalar_one_or_none()

    async def list_categories(
        self,
        department_id: Optional[uuid.UUID] = None,
        active_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Category]:
        stmt = select(Category)
        if department_id is not None:
            stmt = stmt.where(Category.department_id == department_id)
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        stmt = stmt.order_by(Category.name).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, category: Category) -> Category:
        self.db.add(category)
        return category

    async def delete(self, category: Category) -> None:
        await self.db.delete(category)

