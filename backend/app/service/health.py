from app.core.config import settings
from app.repo.health import HealthRepository
from app.schemas.health import HealthResponse


class HealthService:
    """Service kiểm tra tình trạng hoạt động của API và kết nối cơ sở dữ liệu."""

    def __init__(self, health_repo: HealthRepository) -> None:
        self.health_repo = health_repo

    async def check_health(self) -> HealthResponse:
        """Kiểm tra kết nối DB và extension pgvector, trả về trạng thái hệ thống."""
        is_connected = await self.health_repo.check_db_connection()
        pgvector_enabled = False
        if is_connected:
            pgvector_enabled = await self.health_repo.check_pgvector_extension()

        db_status = "connected" if is_connected else "disconnected"

        return HealthResponse(
            status="ok" if is_connected else "degraded",
            service=settings.PROJECT_NAME,
            version=settings.VERSION,
            environment=settings.ENVIRONMENT,
            database=db_status,
            pgvector_enabled=pgvector_enabled,
        )
