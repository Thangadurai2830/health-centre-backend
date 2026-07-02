import uuid

from app.models.user import UserRole


async def _create_district(client, admin_headers) -> dict:
    payload = {
        "name": f"District {uuid.uuid4().hex[:6]}",
        "state": "Stateland",
        "code": f"D{uuid.uuid4().hex[:6]}",
    }
    resp = await client.post("/api/v1/districts", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


async def _create_health_centre(client, admin_headers, district_id: str) -> dict:
    payload = {
        "district_id": district_id,
        "name": f"Centre {uuid.uuid4().hex[:6]}",
        "type": "PHC",
    }
    resp = await client.post("/api/v1/health-centres", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


async def test_assign_staff_happy_path(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    staff = await authed_client_factory(UserRole.DOCTOR)
    district = await _create_district(client, admin.headers)
    centre = await _create_health_centre(client, admin.headers, district["id"])

    resp = await client.post(
        "/api/v1/staff/assign",
        json={"user_id": str(staff.user.id), "health_centre_id": centre["id"]},
        headers=admin.headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "active"
    assert body["user_id"] == str(staff.user.id)


async def test_assign_staff_requires_admin_role(client, authed_client_factory):
    citizen = await authed_client_factory(UserRole.CITIZEN)
    staff = await authed_client_factory(UserRole.DOCTOR)
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)
    centre = await _create_health_centre(client, admin.headers, district["id"])

    resp = await client.post(
        "/api/v1/staff/assign",
        json={"user_id": str(staff.user.id), "health_centre_id": centre["id"]},
        headers=citizen.headers,
    )
    assert resp.status_code == 403


async def test_assign_staff_nonexistent_user_returns_404(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)
    centre = await _create_health_centre(client, admin.headers, district["id"])

    resp = await client.post(
        "/api/v1/staff/assign",
        json={"user_id": str(uuid.uuid4()), "health_centre_id": centre["id"]},
        headers=admin.headers,
    )
    assert resp.status_code == 404


async def test_second_active_assignment_conflicts(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    staff = await authed_client_factory(UserRole.DOCTOR)
    district = await _create_district(client, admin.headers)
    centre1 = await _create_health_centre(client, admin.headers, district["id"])
    centre2 = await _create_health_centre(client, admin.headers, district["id"])

    first = await client.post(
        "/api/v1/staff/assign",
        json={"user_id": str(staff.user.id), "health_centre_id": centre1["id"]},
        headers=admin.headers,
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/staff/assign",
        json={"user_id": str(staff.user.id), "health_centre_id": centre2["id"]},
        headers=admin.headers,
    )
    assert second.status_code == 409


async def test_transfer_staff_moves_assignment(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    staff = await authed_client_factory(UserRole.DOCTOR)
    district = await _create_district(client, admin.headers)
    centre1 = await _create_health_centre(client, admin.headers, district["id"])
    centre2 = await _create_health_centre(client, admin.headers, district["id"])

    await client.post(
        "/api/v1/staff/assign",
        json={"user_id": str(staff.user.id), "health_centre_id": centre1["id"]},
        headers=admin.headers,
    )

    transfer_resp = await client.put(
        "/api/v1/staff/transfer",
        json={"user_id": str(staff.user.id), "health_centre_id": centre2["id"]},
        headers=admin.headers,
    )
    assert transfer_resp.status_code == 200
    transferred = transfer_resp.json()
    assert transferred["status"] == "active"
    assert transferred["health_centre_id"] == centre2["id"]

    centre1_staff = await client.get(
        f"/api/v1/staff/health-centre/{centre1['id']}", headers=admin.headers
    )
    assert centre1_staff.status_code == 200
    statuses = [item["status"] for item in centre1_staff.json()["items"]]
    assert "transferred" in statuses

    centre2_staff = await client.get(
        f"/api/v1/staff/health-centre/{centre2['id']}?status=active", headers=admin.headers
    )
    assert centre2_staff.status_code == 200
    body = centre2_staff.json()
    assert body["total"] == 1
    assert body["items"][0]["user_id"] == str(staff.user.id)


async def test_list_staff_for_health_centre_readable_by_any_authed_user(
    client, authed_client_factory
):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)
    district = await _create_district(client, admin.headers)
    centre = await _create_health_centre(client, admin.headers, district["id"])

    resp = await client.get(f"/api/v1/staff/health-centre/{centre['id']}", headers=citizen.headers)
    assert resp.status_code == 200
