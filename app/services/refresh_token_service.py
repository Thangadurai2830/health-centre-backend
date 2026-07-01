import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedError
from app.core.security import generate_opaque_token
from app.models.refresh_token import RefreshToken


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def issue_refresh_token(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    device: str | None,
    ip_address: str | None,
) -> str:
    raw_token = generate_opaque_token()
    refresh_token = RefreshToken(
        user_id=user_id,
        session_id=session_id,
        token_hash=_hash_token(raw_token),
        device=device,
        ip_address=ip_address,
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES),
    )
    db.add(refresh_token)
    await db.commit()
    return raw_token


async def get_valid_refresh_token(db: AsyncSession, raw_token: str) -> RefreshToken:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == _hash_token(raw_token))
    result = await db.execute(stmt)
    refresh_token = result.scalars().first()

    if refresh_token is None:
        raise UnauthorizedError("Invalid refresh token", error_code="invalid_token")
    if refresh_token.revoked:
        raise UnauthorizedError("Refresh token has been revoked", error_code="invalid_token")
    if refresh_token.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh token has expired", error_code="expired_token")
    return refresh_token


async def revoke_refresh_token(db: AsyncSession, refresh_token: RefreshToken) -> None:
    refresh_token.revoked = True
    await db.commit()


async def revoke_all_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)
    )
    result = await db.execute(stmt)
    for token in result.scalars().all():
        token.revoked = True
    await db.commit()


async def revoke_all_for_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    stmt = select(RefreshToken).where(
        RefreshToken.session_id == session_id, RefreshToken.revoked.is_(False)
    )
    result = await db.execute(stmt)
    for token in result.scalars().all():
        token.revoked = True
    await db.commit()
