from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Lớp Repository cơ sở cung cấp các tiện ích quản lý phiên làm việc (session) với cơ sở dữ liệu."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def commit(self) -> None:
        """Xác nhận lưu transaction vào cơ sở dữ liệu."""
        await self.db.commit()

    async def flush(self) -> None:
        """Đẩy các thay đổi hiện tại vào database mà chưa đóng transaction."""
        await self.db.flush()

    async def refresh(self, instance: Any) -> None:
        """Làm mới dữ liệu của một instance từ database."""
        await self.db.refresh(instance)

    async def rollback(self) -> None:
        """Hoàn tác transaction khi xảy ra lỗi."""
        await self.db.rollback()
