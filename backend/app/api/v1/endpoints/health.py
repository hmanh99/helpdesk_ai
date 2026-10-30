from fastapi import APIRouter

from app.api.deps import HealthServiceDep
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse, summary="Kiểm tra trạng thái API và Database")
async def check_health(health_service: HealthServiceDep) -> HealthResponse:
    """Endpoint kiểm tra trạng thái hoạt động của hệ thống và kết nối cơ sở dữ liệu."""
    return await health_service.check_health()
