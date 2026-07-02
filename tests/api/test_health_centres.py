import uuid

from app.models.user import UserRole


async def _create_district(client, admin_headers, code: str | None = None) -> dict:
    payload = {
        "name": f"District {uuid.uuid4().hex[:6]}",
        "state": "Stateland",
        "code": code or f"D{uuid.uuid4().hex[:6]}",
    }
    resp = await client.post("/api/v1/districts", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


def _centre_payload(district_id: str, **overrides) -> dict:
    payload = {
        "district_id": district_id,
        "name": f"Centre {uuid.uuid4().hex[:6]}",
        "type": "PHC",
        "latitude": 12.5,
        "longitude": 77.5,
        "phone": "+919876543210",
    }
    payload.update(overrides)
    return payload


async def test_create_and_get_health_centre(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)

    create_resp = await client.post(
        "/api/v1/health-centres", json=_centre_payload(district["id"]), headers=admin.headers
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["status"] == "active"

    get_resp = await client.get(f"/api/v1/health-centres/{created['id']}", headers=admin.headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == created["id"]


async def test_health_centre_write_requires_admin(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)
    district = await _create_district(client, admin.headers)

    resp = await client.post(
        "/api/v1/health-centres", json=_centre_payload(district["id"]), headers=citizen.headers
    )
    assert resp.status_code == 403

    list_resp = await client.get("/api/v1/health-centres", headers=citizen.headers)
    assert list_resp.status_code == 200


async def test_health_centre_invalid_gps_returns_422(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)

    resp = await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(district["id"], latitude=999.0),
        headers=admin.headers,
    )
    assert resp.status_code == 422


async def test_health_centre_invalid_phone_returns_422(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)

    resp = await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(district["id"], phone="not-a-phone!!"),
        headers=admin.headers,
    )
    assert resp.status_code == 422


async def test_health_centre_duplicate_name_in_district_conflicts(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)
    payload = _centre_payload(district["id"], name="Same Name Centre")

    first = await client.post("/api/v1/health-centres", json=payload, headers=admin.headers)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(district["id"], name="Same Name Centre"),
        headers=admin.headers,
    )
    assert second.status_code == 409


async def test_health_centre_nonexistent_district_returns_404(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    resp = await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(str(uuid.uuid4())),
        headers=admin.headers,
    )
    assert resp.status_code == 404


async def test_health_centre_filter_by_district(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district1 = await _create_district(client, admin.headers)
    district2 = await _create_district(client, admin.headers)

    await client.post(
        "/api/v1/health-centres", json=_centre_payload(district1["id"]), headers=admin.headers
    )
    await client.post(
        "/api/v1/health-centres", json=_centre_payload(district2["id"]), headers=admin.headers
    )

    resp = await client.get(
        f"/api/v1/health-centres?district_id={district1['id']}", headers=admin.headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["district_id"] == district1["id"]


async def test_health_centre_search_by_name(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)

    await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(district["id"], name="Sunrise PHC"),
        headers=admin.headers,
    )
    await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(district["id"], name="Moonlight CHC"),
        headers=admin.headers,
    )

    resp = await client.get("/api/v1/health-centres?search=sunrise", headers=admin.headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Sunrise PHC"


async def test_health_centre_nearby(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)

    near = await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(district["id"], latitude=12.50, longitude=77.50),
        headers=admin.headers,
    )
    assert near.status_code == 201

    far = await client.post(
        "/api/v1/health-centres",
        json=_centre_payload(district["id"], latitude=45.0, longitude=90.0),
        headers=admin.headers,
    )
    assert far.status_code == 201

    resp = await client.get(
        "/api/v1/health-centres/nearby?lat=12.50&lng=77.51&radius_km=50",
        headers=admin.headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    names = [item["name"] for item in body]
    assert near.json()["name"] in names
    assert far.json()["name"] not in names


async def test_health_centre_pagination(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)
    for _ in range(4):
        await client.post(
            "/api/v1/health-centres", json=_centre_payload(district["id"]), headers=admin.headers
        )

    resp = await client.get("/api/v1/health-centres?limit=2&offset=0", headers=admin.headers)
    body = resp.json()
    assert body["total"] == 4
    assert len(body["items"]) == 2


async def test_delete_health_centre(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)
    created = (
        await client.post(
            "/api/v1/health-centres", json=_centre_payload(district["id"]), headers=admin.headers
        )
    ).json()

    delete_resp = await client.delete(
        f"/api/v1/health-centres/{created['id']}", headers=admin.headers
    )
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/health-centres/{created['id']}", headers=admin.headers)
    assert get_resp.status_code == 404
