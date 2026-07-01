import uuid
from collections.abc import AsyncGenerator, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_token
from app.db.redis import get_redis as _get_redis
from app.db.session import get_db
from app.models.session import SessionStatus
from app.models.user import User, UserRole, UserStatus
from app.services import session_service, user_service

bearer_scheme = HTTPBearer(auto_error=False)


async def get_session(db: AsyncSession = Depends(get_db)) -> AsyncGenerator[AsyncSession, None]:
    yield db


def get_redis() -> Redis:
    return _get_redis()


class TokenPayload:
    def __init__(self, user_id: str, role: str, session_id: str, version: int) -> None:
        self.user_id = user_id
        self.role = role
        self.session_id = session_id
        self.version = version


async def get_current_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> TokenPayload:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token", error_code="unauthorized")

    try:
        payload = decode_token(credentials.credentials)
    except PyJWTError as exc:
        raise UnauthorizedError("Invalid or expired token", error_code="invalid_token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Token is not an access token", error_code="invalid_token")

    user_id = payload.get("sub")
    role = payload.get("role")
    session_id = payload.get("sid")
    version = payload.get("ver")
    if user_id is None or role is None or session_id is None or version is None:
        raise UnauthorizedError("Malformed token", error_code="invalid_token")

    return TokenPayload(user_id=user_id, role=role, session_id=session_id, version=version)


async def get_current_user(
    token: TokenPayload = Depends(get_current_token),
    db: AsyncSession = Depends(get_session),
) -> User:
    try:
        user_id = uuid.UUID(token.user_id)
    except ValueError as exc:
        raise UnauthorizedError("Malformed token", error_code="invalid_token") from exc

    try:
        user = await user_service.get_user_by_id(db, user_id)
    except NotFoundError as exc:
        raise UnauthorizedError("User no longer exists", error_code="invalid_token") from exc

    if user.token_version != token.version:
        raise UnauthorizedError("Token has been invalidated", error_code="invalid_token")

    if user.status != UserStatus.ACTIVE:
        raise ForbiddenError("User account is not active", error_code="inactive_user")

    try:
        session_id = uuid.UUID(token.session_id)
    except ValueError as exc:
        raise UnauthorizedError("Malformed token", error_code="invalid_token") from exc

    try:
        session = await session_service.get_session(db, session_id)
    except NotFoundError as exc:
        raise UnauthorizedError("Session no longer exists", error_code="invalid_token") from exc

    if session.status != SessionStatus.ACTIVE:
        raise UnauthorizedError("Session is no longer active", error_code="invalid_token")

    await session_service.touch_session(db, session)

    return user


def require_roles(*allowed_roles: UserRole) -> Callable:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise ForbiddenError(
                "You do not have permission to perform this action", error_code="forbidden"
            )
        return user

    return dependency
