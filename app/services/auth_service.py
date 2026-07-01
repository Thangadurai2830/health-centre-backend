import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token
from app.models.otp import OtpPurpose
from app.models.session import SessionStatus
from app.models.user import User, UserRole
from app.schemas.auth import DeviceInfo, TokenResponse
from app.services import otp_service, refresh_token_service, session_service, user_service


async def login_with_otp(
    db: AsyncSession,
    *,
    mobile_number: str,
    country_code: str,
    otp_code: str,
    device: DeviceInfo | None,
    ip_address: str | None,
) -> TokenResponse:
    await otp_service.verify_otp(
        db, mobile_number=mobile_number, otp_code=otp_code, purpose=OtpPurpose.LOGIN
    )

    user, is_new_user = await user_service.get_or_create_user(
        db, mobile_number=mobile_number, country_code=country_code
    )
    await user_service.mark_login(db, user)

    session = await session_service.create_session(
        db, user_id=user.id, device=device, ip_address=ip_address
    )

    access_token, refresh_token = await _issue_token_pair(
        db,
        user=user,
        session_id=session.id,
        device=device.device_name if device else None,
        ip_address=ip_address,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        is_new_user=is_new_user,
        user=user_service.to_profile_read(user),
    )


async def refresh_access_token(db: AsyncSession, *, raw_refresh_token: str) -> tuple[str, int]:
    stored_token = await refresh_token_service.get_valid_refresh_token(db, raw_refresh_token)
    user = await user_service.get_user_by_id(db, stored_token.user_id)

    access_token = create_access_token(
        str(user.id),
        role=UserRole(user.role).value,
        session_id=str(stored_token.session_id),
        version=user.token_version,
    )
    return access_token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


async def logout(db: AsyncSession, *, raw_refresh_token: str) -> None:
    stored_token = await refresh_token_service.get_valid_refresh_token(db, raw_refresh_token)
    await refresh_token_service.revoke_refresh_token(db, stored_token)
    session = await session_service.get_session(db, stored_token.session_id)
    await session_service.end_session(db, session, status=SessionStatus.LOGGED_OUT)


async def logout_all(db: AsyncSession, *, user: User) -> None:
    user.token_version += 1
    await db.commit()
    await refresh_token_service.revoke_all_for_user(db, user.id)
    await session_service.end_all_sessions(db, user.id)


async def _issue_token_pair(
    db: AsyncSession,
    *,
    user: User,
    session_id: uuid.UUID,
    device: str | None,
    ip_address: str | None,
) -> tuple[str, str]:
    access_token = create_access_token(
        str(user.id),
        role=UserRole(user.role).value,
        session_id=str(session_id),
        version=user.token_version,
    )
    refresh_token = await refresh_token_service.issue_refresh_token(
        db, user_id=user.id, session_id=session_id, device=device, ip_address=ip_address
    )
    return access_token, refresh_token
