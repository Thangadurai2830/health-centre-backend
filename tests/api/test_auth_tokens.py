MOBILE = "9123456701"


async def _login(client, sent_otps, mobile: str = MOBILE) -> dict:
    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": mobile, "country_code": "+91"}
    )
    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": mobile, "country_code": "+91", "otp_code": sent_otps[mobile]},
    )
    assert response.status_code == 200
    return response.json()


async def test_jwt_access_token_has_expected_claims(client, sent_otps):
    import jwt as pyjwt

    from app.core.config import settings

    tokens = await _login(client, sent_otps)
    payload = pyjwt.decode(
        tokens["access_token"], settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == tokens["user"]["id"]
    assert payload["role"] == "citizen"
    assert payload["type"] == "access"
    assert "sid" in payload
    assert "ver" in payload
    assert "iat" in payload
    assert "exp" in payload


async def test_me_with_valid_access_token(client, sent_otps):
    tokens = await _login(client, sent_otps)
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["mobile_number"] == MOBILE


async def test_protected_route_rejects_missing_token(client):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error_code"] == "unauthorized"


async def test_protected_route_rejects_garbage_token(client):
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_token"


async def test_refresh_returns_new_access_token(client, sent_otps):
    tokens = await _login(client, sent_otps)
    response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body

    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["mobile_number"] == MOBILE


async def test_refresh_rejects_invalid_token(client):
    response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "bogus"})
    assert response.status_code == 401
    assert response.json()["error_code"] == "invalid_token"


async def test_logout_revokes_refresh_token_and_session(client, sent_otps):
    tokens = await _login(client, sent_otps)

    logout_response = await client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    refresh_response = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error_code"] == "invalid_token"

    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_response.status_code == 401


async def test_logout_all_invalidates_all_tokens(client, sent_otps):
    tokens = await _login(client, sent_otps)

    response = await client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 204

    me_response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me_response.status_code == 401
    assert me_response.json()["error_code"] == "invalid_token"
