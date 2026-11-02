from sqlalchemy import text

from app.repo.base import BaseRepository


class HealthRepository(BaseRepository):
    """Repository phụ trách kiểm tra tình trạng kết nối cơ sở dữ liệu và extension."""

    async def check_db_connection(self) -> bool:
        """Kiểm tra kết nối tới cơ sở dữ liệu thông qua SELECT 1."""
        try:
            await self.db.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    async def check_pgvector_extension(self) -> bool:
        """Kiểm tra extension pgvector đã được kích hoạt trong PostgreSQL hay chưa."""
        try:
            result = await self.db.execute(
                text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            return bool(result.scalar())
        except Exception:
            return False
