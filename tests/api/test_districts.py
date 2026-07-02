import uuid

from app.models.user import UserRole


async def _make_district_payload(**overrides):
    payload = {"name": "Alpha District", "state": "Stateland", "code": f"D{uuid.uuid4().hex[:6]}"}
    payload.update(overrides)
    return payload


async def test_create_and_get_district(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    payload = await _make_district_payload()

    create_resp = await client.post("/api/v1/districts", json=payload, headers=admin.headers)
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["name"] == payload["name"]
    assert created["status"] == "active"

    get_resp = await client.get(f"/api/v1/districts/{created['id']}", headers=admin.headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == created["id"]


async def test_update_and_delete_district(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    payload = await _make_district_payload()
    created = (await client.post("/api/v1/districts", json=payload, headers=admin.headers)).json()

    update_resp = await client.put(
        f"/api/v1/districts/{created['id']}",
        json={"name": "Beta District"},
        headers=admin.headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Beta District"

    delete_resp = await client.delete(f"/api/v1/districts/{created['id']}", headers=admin.headers)
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/districts/{created['id']}", headers=admin.headers)
    assert get_resp.status_code == 404


async def test_district_write_requires_admin_role(client, authed_client_factory):
    citizen = await authed_client_factory(UserRole.CITIZEN)
    payload = await _make_district_payload()

    create_resp = await client.post("/api/v1/districts", json=payload, headers=citizen.headers)
    assert create_resp.status_code == 403

    list_resp = await client.get("/api/v1/districts", headers=citizen.headers)
    assert list_resp.status_code == 200


async def test_district_requires_authentication(client):
    response = await client.get("/api/v1/districts")
    assert response.status_code == 401


async def test_duplicate_district_code_conflicts(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    payload = await _make_district_payload(code="DUPCODE")

    first = await client.post("/api/v1/districts", json=payload, headers=admin.headers)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/districts",
        json=await _make_district_payload(code="DUPCODE"),
        headers=admin.headers,
    )
    assert second.status_code == 409


async def test_district_not_found(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    response = await client.get(f"/api/v1/districts/{uuid.uuid4()}", headers=admin.headers)
    assert response.status_code == 404


async def test_district_pagination(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    for i in range(5):
        await client.post(
            "/api/v1/districts",
            json=await _make_district_payload(name=f"District {i}", code=f"P{i}CODE"),
            headers=admin.headers,
        )

    page1 = await client.get("/api/v1/districts?limit=2&offset=0", headers=admin.headers)
    assert page1.status_code == 200
    body1 = page1.json()
    assert body1["total"] == 5
    assert len(body1["items"]) == 2
    assert body1["limit"] == 2
    assert body1["offset"] == 0

    page2 = await client.get("/api/v1/districts?limit=2&offset=2", headers=admin.headers)
    body2 = page2.json()
    assert len(body2["items"]) == 2
    assert body2["items"] != body1["items"]


async def test_district_search_by_name(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    await client.post(
        "/api/v1/districts",
        json=await _make_district_payload(name="Zephyr Zone", code="ZZ001"),
        headers=admin.headers,
    )
    await client.post(
        "/api/v1/districts",
        json=await _make_district_payload(name="Other Place", code="OP001"),
        headers=admin.headers,
    )

    response = await client.get("/api/v1/districts?search=zephyr", headers=admin.headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Zephyr Zone"


async def test_delete_district_conflict_when_referenced(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = (
        await client.post(
            "/api/v1/districts", json=await _make_district_payload(), headers=admin.headers
        )
    ).json()
    await client.post(
        "/api/v1/blocks",
        json={"district_id": district["id"], "name": "Block A", "code": "BLOCKA"},
        headers=admin.headers,
    )

    delete_resp = await client.delete(f"/api/v1/districts/{district['id']}", headers=admin.headers)
    assert delete_resp.status_code == 409
