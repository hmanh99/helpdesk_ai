from typing import Optional, Sequence
import uuid

from sqlalchemy import select

from app.models.department import Department
from app.repo.base import BaseRepository


class DepartmentRepository(BaseRepository):
    """Repository quản lý các thao tác cơ sở dữ liệu đối với bảng Department."""

    async def get_by_id(self, dept_id: uuid.UUID) -> Optional[Department]:
        """Tìm phòng ban theo ID."""
        result = await self.db.execute(select(Department).where(Department.id == dept_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[Department]:
        """Tìm phòng ban theo tên."""
        result = await self.db.execute(
            select(Department).where(Department.name == name.strip())
        )
        return result.scalar_one_or_none()

    async def list_departments(self, skip: int = 0, limit: int = 50) -> Sequence[Department]:
        """Lấy danh sách các phòng ban với phân trang."""
        result = await self.db.execute(
            select(Department).offset(skip).limit(limit).order_by(Department.name)
        )
        return result.scalars().all()

    async def create(self, department: Department) -> Department:
        """Thêm mới phòng ban vào cơ sở dữ liệu."""
        self.db.add(department)
        return department
