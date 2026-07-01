from redis.asyncio import Redis

from app.core.config import settings


def _cooldown_key(mobile_number: str, country_code: str) -> str:
    return f"otp:cooldown:{country_code}{mobile_number}"


async def is_resend_on_cooldown(redis: Redis, mobile_number: str, country_code: str) -> bool:
    return await redis.exists(_cooldown_key(mobile_number, country_code)) == 1


async def start_resend_cooldown(redis: Redis, mobile_number: str, country_code: str) -> None:
    await redis.set(
        _cooldown_key(mobile_number, country_code),
        "1",
        ex=settings.OTP_RESEND_COOLDOWN_SECONDS,
    )
