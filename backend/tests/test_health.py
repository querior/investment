import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app

@pytest.mark.anyio
async def test_health_ok():
    app = create_app()

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test"
    ) as ac:
        r = await ac.get("/api/health")

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
