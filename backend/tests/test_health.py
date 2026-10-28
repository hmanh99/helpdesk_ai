from httpx import ASGITransport, AsyncClient
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Helpdesk AI API"
    assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "Helpdesk AI API"
    assert data["status"] in ("ok", "degraded")

