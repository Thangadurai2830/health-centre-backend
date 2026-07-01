import uuid

from fastapi import APIRouter, Depends, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_redis, get_session
from app.core.config import settings
from app.models.otp import OtpPurpose
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    CheckMobileResponse,
    LogoutRequest,
    RefreshTokenRequest,
    SendOtpRequest,
    SendOtpResponse,
    SessionRead,
    TokenResponse,
    VerifyOtpRequest,
)
from app.schemas.common import ErrorResponse
from app.schemas.user import UserProfileRead, UserProfileUpdate
from app.services import (
    auth_service,
    otp_service,
    refresh_token_service,
    session_service,
    user_service,
)

router = APIRouter()


@router.post(
    "/send-otp",
    response_model=SendOtpResponse,
    summary="Send OTP to a mobile number",
    description=(
        "Generates a 6-digit OTP, hashes and stores it, invalidates any previously active "
        "OTP for the same mobile number, and dispatches it via the mock SMS service "
        "(the OTP is written to the application logs). Subject to a 60-second resend cooldown."
    ),
    tags=["auth"],
    responses={
        422: {"model": ErrorResponse, "description": "Invalid mobile number or country code"},
        429: {"model": ErrorResponse, "description": "Resend cooldown still active"},
    },
)
async def send_otp(
    payload: SendOtpRequest,
    db: AsyncSession = Depends(get_session),
    redis: Redis = Depends(get_redis),
) -> SendOtpResponse:
    await otp_service.send_otp(
        db,
        redis,
        mobile_number=payload.mobile_number,
        country_code=payload.country_code,
        purpose=OtpPurpose.LOGIN,
    )
    return SendOtpResponse(
        message="OTP sent successfully",
        mobile_number=payload.mobile_number,
        expires_in_seconds=settings.OTP_EXPIRE_MINUTES * 60,
        resend_allowed_in_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
    )


@router.post(
    "/verify-otp",
    response_model=TokenResponse,
    summary="Verify OTP and authenticate",
    description=(
        "Verifies the OTP for the given mobile number. Creates a new user if one does not "
        "already exist, creates a session, and issues a JWT access token and refresh token."
    ),
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid, expired, or exhausted OTP"},
    },
)
async def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> TokenResponse:
    return await auth_service.login_with_otp(
        db,
        mobile_number=payload.mobile_number,
        country_code=payload.country_code,
        otp_code=payload.otp_code,
        device=payload.device,
        ip_address=request.client.host if request.client else None,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenResponse,
    summary="Refresh access token",
    description="Exchanges a valid, non-revoked refresh token for a new access token.",
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid, revoked, or expired refresh token"},
    },
)
async def refresh(
    payload: RefreshTokenRequest, db: AsyncSession = Depends(get_session)
) -> AccessTokenResponse:
    access_token, expires_in = await auth_service.refresh_access_token(
        db, raw_refresh_token=payload.refresh_token
    )
    return AccessTokenResponse(access_token=access_token, expires_in=expires_in)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout current session",
    description="Revokes the given refresh token and ends its associated session.",
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid or already-revoked refresh token"},
    },
)
async def logout(payload: LogoutRequest, db: AsyncSession = Depends(get_session)) -> None:
    await auth_service.logout(db, raw_refresh_token=payload.refresh_token)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout from all sessions",
    description=(
        "Invalidates every access and refresh token issued to the current user by bumping "
        "the user's token version, and ends all active sessions."
    ),
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def logout_all(
    db: AsyncSession = Depends(get_session), user: User = Depends(get_current_user)
) -> None:
    await auth_service.logout_all(db, user=user)


@router.get(
    "/me",
    response_model=UserProfileRead,
    summary="Get current user profile",
    description="Returns the minimal profile of the currently authenticated user.",
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def get_me(user: User = Depends(get_current_user)) -> UserProfileRead:
    return user_service.to_profile_read(user)


@router.patch(
    "/profile",
    response_model=UserProfileRead,
    summary="Update current user profile",
    description="Updates mutable profile fields (name, email, language) for the current user.",
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def update_profile(
    payload: UserProfileUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> UserProfileRead:
    updated_user = await user_service.update_profile(db, user, payload)
    return user_service.to_profile_read(updated_user)


@router.get(
    "/sessions",
    response_model=list[SessionRead],
    summary="List active sessions",
    description="Lists all active sessions for the current user, most recently active first.",
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_sessions(
    request: Request,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[SessionRead]:
    sessions = await session_service.list_active_sessions(db, user.id)
    current_ip = request.client.host if request.client else None
    return [
        SessionRead(
            id=s.id,
            device_name=s.device_name,
            device_type=s.device_type,
            device_os=s.device_os,
            browser=s.browser,
            ip_address=s.ip_address,
            location=s.location,
            login_time=s.login_time,
            last_activity=s.last_activity,
            status=s.status.value if hasattr(s.status, "value") else s.status,
            is_current=s.ip_address == current_ip,
        )
        for s in sessions
    ]


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a session",
    description="Revokes a specific session belonging to the current user and its refresh tokens.",
    tags=["auth"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Session belongs to a different user"},
        404: {"model": ErrorResponse, "description": "Session not found"},
    },
)
async def revoke_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    await session_service.revoke_session_for_user(db, user_id=user.id, session_id=session_id)
    await refresh_token_service.revoke_all_for_session(db, session_id)


@router.get(
    "/check-mobile",
    response_model=CheckMobileResponse,
    summary="Check if a mobile number is registered",
    description="Checks whether a user already exists for the given mobile number.",
    tags=["auth"],
)
async def check_mobile(
    mobile_number: str, db: AsyncSession = Depends(get_session)
) -> CheckMobileResponse:
    user = await user_service.get_user_by_mobile(db, mobile_number)
    if user is None:
        return CheckMobileResponse(exists=False)
    return CheckMobileResponse(exists=True, is_verified=user.is_verified)
