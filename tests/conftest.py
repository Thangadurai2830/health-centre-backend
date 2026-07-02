import os
import uuid
from dataclasses import dataclass

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.db import redis as redis_module
from app.db.session import engine, get_db
from app.main import app
from app.models.user import User, UserRole, UserStatus
from app.services import mock_otp_service, session_service

AUTH_TABLES = (
    "staff_assignments",
    "rooms",
    "wards",
    "health_centres",
    "villages",
    "blocks",
    "districts",
    "departments",
    "specializations",
    "refresh_tokens",
    "sessions",
    "otps",
    "users",
)


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


@pytest.fixture
async def db_session() -> AsyncSession:
    async for session in get_db():
        yield session


@dataclass
class AuthedUser:
    user: User
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def authed_client_factory(db_session: AsyncSession):
    """Creates a User + Session directly in the DB and mints a matching access token.

    Bypasses the OTP flow entirely so tests can quickly get a bearer token for a
    user of any role, per the pattern used in tests/services/test_require_roles.py.
    """

    async def _make(
        role: UserRole = UserRole.CITIZEN, *, mobile_number: str | None = None
    ) -> AuthedUser:
        mobile = mobile_number or f"9{uuid.uuid4().int % 10**9:09d}"
        user = User(
            mobile_number=mobile,
            country_code="+91",
            role=role,
            status=UserStatus.ACTIVE,
            is_verified=True,
            token_version=0,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        session = await session_service.create_session(
            db_session, user_id=user.id, device=None, ip_address="127.0.0.1"
        )

        token = create_access_token(
            str(user.id),
            role=role.value,
            session_id=str(session.id),
            version=user.token_version,
        )
        return AuthedUser(user=user, token=token)

    return _make
