import os

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text

from app.db import redis as redis_module
from app.db.session import engine
from app.main import app
from app.services import mock_otp_service

AUTH_TABLES = ("refresh_tokens", "sessions", "otps", "users")


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(autouse=True)
async def _clean_state():
    yield
    async with engine.begin() as conn:
        for table in AUTH_TABLES:
            await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
    await engine.dispose()

    redis = Redis(connection_pool=redis_module.redis_pool)
    await redis.flushdb()
    await redis.aclose()
    await redis_module.redis_pool.disconnect()


@pytest.fixture
def sent_otps(monkeypatch):
    captured: dict[str, str] = {}

    async def fake_send(mobile_number: str, country_code: str, otp_code: str) -> None:
        captured[mobile_number] = otp_code

    monkeypatch.setattr(mock_otp_service, "send_otp_sms", fake_send)
    return captured
