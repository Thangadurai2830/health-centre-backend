from datetime import UTC, datetime, timedelta

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import TooManyRequestsError, UnauthorizedError
from app.core.security import generate_otp_code, hash_password, verify_password
from app.models.otp import Otp, OtpPurpose
from app.services import mock_otp_service, otp_rate_limit


async def send_otp(
    db: AsyncSession,
    redis: Redis,
    *,
    mobile_number: str,
    country_code: str,
    purpose: OtpPurpose = OtpPurpose.LOGIN,
) -> Otp:
    if await otp_rate_limit.is_resend_on_cooldown(redis, mobile_number, country_code):
        raise TooManyRequestsError(
            "Please wait before requesting another OTP", error_code="otp_resend_cooldown"
        )

    stmt = select(Otp).where(
        Otp.mobile_number == mobile_number,
        Otp.purpose == purpose,
        Otp.verified.is_(False),
    )
    result = await db.execute(stmt)
    for previous_otp in result.scalars().all():
        previous_otp.verified = True  # invalidate previous active OTP

    otp_code = generate_otp_code(settings.OTP_LENGTH)
    otp = Otp(
        mobile_number=mobile_number,
        otp_hash=hash_password(otp_code),
        expires_at=datetime.now(UTC) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
        purpose=purpose,
    )
    db.add(otp)
    await db.commit()
    await db.refresh(otp)

    await mock_otp_service.send_otp_sms(mobile_number, country_code, otp_code)
    await otp_rate_limit.start_resend_cooldown(redis, mobile_number, country_code)
    return otp


async def verify_otp(
    db: AsyncSession,
    *,
    mobile_number: str,
    otp_code: str,
    purpose: OtpPurpose = OtpPurpose.LOGIN,
) -> Otp:
    stmt = (
        select(Otp)
        .where(
            Otp.mobile_number == mobile_number,
            Otp.purpose == purpose,
            Otp.verified.is_(False),
        )
        .order_by(Otp.created_at.desc())
    )
    result = await db.execute(stmt)
    otp = result.scalars().first()

    if otp is None:
        raise UnauthorizedError(
            "No active OTP found for this mobile number", error_code="invalid_otp"
        )

    if otp.expires_at < datetime.now(UTC):
        raise UnauthorizedError("OTP has expired", error_code="expired_otp")

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise UnauthorizedError(
            "Maximum OTP verification attempts exceeded", error_code="too_many_attempts"
        )

    otp.attempts += 1

    if not verify_password(otp_code, otp.otp_hash):
        await db.commit()
        raise UnauthorizedError("Invalid OTP", error_code="invalid_otp")

    otp.verified = True
    await db.commit()
    await db.refresh(otp)
    return otp
