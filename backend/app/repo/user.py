from typing import Optional, Sequence
import uuid

from sqlalchemy import func, select

from app.models.user import AppUser, UserRole
from app.repo.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository quản lý các thao tác cơ sở dữ liệu đối với bảng AppUser."""

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[AppUser]:
        """Tìm người dùng theo UUID."""
        result = await self.db.execute(select(AppUser).where(AppUser.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[AppUser]:
        """Tìm người dùng theo email (không phân biệt chữ hoa, chữ thường)."""
        normalized = email.strip().lower()
        result = await self.db.execute(
            select(AppUser).where(func.lower(AppUser.email) == normalized)
        )
        return result.scalar_one_or_none()

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        department_id: Optional[uuid.UUID] = None,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
    ) -> Sequence[AppUser]:
        """Lấy danh sách người dùng có phân trang và bộ lọc."""
        query = select(AppUser)
        if department_id is not None:
            query = query.where(AppUser.department_id == department_id)
        if role is not None:
            query = query.where(AppUser.role == role)
        if is_active is not None:
            query = query.where(AppUser.is_active == is_active)

        query = query.offset(skip).limit(limit).order_by(AppUser.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_by_department(self, department_id: uuid.UUID) -> Sequence[AppUser]:
        """Lấy danh sách người dùng thuộc một phòng ban cụ thể."""
        result = await self.db.execute(
            select(AppUser)
            .where(AppUser.department_id == department_id)
            .order_by(AppUser.full_name)
        )
        return result.scalars().all()

    async def count_other_active_admins(self, exclude_user_id: uuid.UUID) -> int:
        """Đếm số lượng ADMIN đang hoạt động khác ngoài user_id được chỉ định."""
        result = await self.db.execute(
            select(func.count(AppUser.id)).where(
                AppUser.role == UserRole.ADMIN,
                AppUser.is_active.is_(True),
                AppUser.id != exclude_user_id,
            )
        )
        return result.scalar() or 0

    async def create(self, user: AppUser) -> AppUser:
        """Thêm mới người dùng vào database."""
        self.db.add(user)
        return user

    async def update(self, user: AppUser) -> AppUser:
        """Cập nhật dữ liệu người dùng."""
        return user

    async def delete(self, user: AppUser) -> None:
        """Xóa người dùng khỏi database."""
        await self.db.delete(user)
