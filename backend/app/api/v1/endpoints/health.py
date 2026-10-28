from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.config import settings
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("", response_model=HealthResponse, summary="Check API and Database Health")
async def check_health(db: SessionDep) -> HealthResponse:
    db_status = "disconnected"
    pgvector_enabled = False

    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"

        ext_result = await db.execute(
            text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        pgvector_enabled = bool(ext_result.scalar())
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        database=db_status,
        pgvector_enabled=pgvector_enabled,
    )

