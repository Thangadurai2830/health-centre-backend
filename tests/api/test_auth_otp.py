MOBILE = "9123456700"


async def test_send_otp_success(client, sent_otps):
    response = await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mobile_number"] == MOBILE
    assert MOBILE in sent_otps
    assert len(sent_otps[MOBILE]) == 6


async def test_send_otp_invalid_mobile(client, sent_otps):
    response = await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": "12345", "country_code": "+91"}
    )
    assert response.status_code == 422


async def test_send_otp_resend_cooldown(client, sent_otps):
    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    response = await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    assert response.status_code == 429
    assert response.json()["error_code"] == "otp_resend_cooldown"


async def test_verify_otp_success_creates_user(client, sent_otps):
    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    otp_code = sent_otps[MOBILE]

    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": otp_code},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_new_user"] is True
    assert body["user"]["mobile_number"] == MOBILE
    assert "access_token" in body
    assert "refresh_token" in body


async def test_verify_otp_wrong_code(client, sent_otps):
    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": "000000"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_otp"


async def test_verify_otp_expired(client, sent_otps):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from app.db.session import AsyncSessionLocal
    from app.models.otp import Otp

    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    otp_code = sent_otps[MOBILE]

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Otp).where(Otp.mobile_number == MOBILE))
        otp = result.scalars().first()
        otp.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()

    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": otp_code},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "expired_otp"


async def test_verify_otp_too_many_attempts(client, sent_otps):
    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    otp_code = sent_otps[MOBILE]

    for _ in range(5):
        await client.post(
            "/api/v1/auth/verify-otp",
            json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": "000000"},
        )

    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": otp_code},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "too_many_attempts"


async def test_verify_otp_no_active_otp(client, sent_otps):
    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": "123456"},
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_otp"


async def test_verify_otp_login_existing_user_is_not_new(client, sent_otps):
    from redis.asyncio import Redis

    from app.db.redis import redis_pool

    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    first_response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": sent_otps[MOBILE]},
    )
    assert first_response.json()["is_new_user"] is True

    redis = Redis(connection_pool=redis_pool)
    await redis.flushdb()
    await redis.aclose()

    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": MOBILE, "country_code": "+91"}
    )
    second_response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": MOBILE, "country_code": "+91", "otp_code": sent_otps[MOBILE]},
    )
    assert second_response.status_code == 200
    assert second_response.json()["is_new_user"] is False
