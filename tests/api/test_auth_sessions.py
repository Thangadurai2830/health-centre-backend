MOBILE = "9123456702"


async def _login(client, sent_otps, mobile: str = MOBILE) -> dict:
    await client.post(
        "/api/v1/auth/send-otp", json={"mobile_number": mobile, "country_code": "+91"}
    )
    response = await client.post(
        "/api/v1/auth/verify-otp",
        json={"mobile_number": mobile, "country_code": "+91", "otp_code": sent_otps[mobile]},
    )
    return response.json()


async def test_session_created_on_login(client, sent_otps):
    tokens = await _login(client, sent_otps)
    response = await client.get(
        "/api/v1/auth/sessions", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) == 1
    assert sessions[0]["status"] == "active"


async def test_revoke_session(client, sent_otps):
    tokens = await _login(client, sent_otps)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    sessions = (await client.get("/api/v1/auth/sessions", headers=headers)).json()
    session_id = sessions[0]["id"]

    response = await client.delete(f"/api/v1/auth/sessions/{session_id}", headers=headers)
    assert response.status_code == 204

    me_response = await client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 401


async def test_revoke_session_not_found(client, sent_otps):
    import uuid

    tokens = await _login(client, sent_otps)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.delete(f"/api/v1/auth/sessions/{uuid.uuid4()}", headers=headers)
    assert response.status_code == 404


async def test_check_mobile_exists(client, sent_otps):
    await _login(client, sent_otps)
    response = await client.get(f"/api/v1/auth/check-mobile?mobile_number={MOBILE}")
    assert response.status_code == 200
    assert response.json() == {"exists": True, "is_verified": True}


async def test_check_mobile_not_exists(client):
    response = await client.get("/api/v1/auth/check-mobile?mobile_number=9999999999")
    assert response.status_code == 200
    assert response.json() == {"exists": False, "is_verified": False}


async def test_update_profile(client, sent_otps):
    tokens = await _login(client, sent_otps)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = await client.patch(
        "/api/v1/auth/profile",
        headers=headers,
        json={"full_name": "Jane Doe", "email": "jane@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Jane Doe"
    assert body["email"] == "jane@example.com"
    assert body["profile_completion_percent"] == 100
