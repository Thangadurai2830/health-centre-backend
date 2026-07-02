"""Lighter smoke tests for master-data resources not covered in dedicated test modules.

Covers CRUD happy-path, RBAC, basic validation/conflict handling, and parent-id
filtering for Block, Village, Department, Ward, Room, Specialization, and Lookups.
"""

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


async def _create_block(client, admin_headers, district_id: str) -> dict:
    payload = {
        "district_id": district_id,
        "name": f"Block {uuid.uuid4().hex[:6]}",
        "code": f"B{uuid.uuid4().hex[:6]}",
    }
    resp = await client.post("/api/v1/blocks", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


async def _create_village(client, admin_headers, block_id: str) -> dict:
    payload = {"block_id": block_id, "name": f"Village {uuid.uuid4().hex[:6]}"}
    resp = await client.post("/api/v1/villages", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


async def _create_department(client, admin_headers) -> dict:
    payload = {"name": f"Department {uuid.uuid4().hex[:6]}"}
    resp = await client.post("/api/v1/departments", json=payload, headers=admin_headers)
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


async def _create_ward(client, admin_headers, health_centre_id: str, department_id: str) -> dict:
    payload = {
        "health_centre_id": health_centre_id,
        "department_id": department_id,
        "name": f"Ward {uuid.uuid4().hex[:6]}",
    }
    resp = await client.post("/api/v1/wards", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    return resp.json()


async def test_block_crud_and_rbac(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)
    district = await _create_district(client, admin.headers)

    create_resp = await client.post(
        "/api/v1/blocks",
        json={"district_id": district["id"], "name": "Block One", "code": "BLK1"},
        headers=citizen.headers,
    )
    assert create_resp.status_code == 403

    block = await _create_block(client, admin.headers, district["id"])

    get_resp = await client.get(f"/api/v1/blocks/{block['id']}", headers=citizen.headers)
    assert get_resp.status_code == 200

    filter_resp = await client.get(
        f"/api/v1/blocks?district_id={district['id']}", headers=admin.headers
    )
    assert filter_resp.status_code == 200
    assert filter_resp.json()["total"] == 1

    update_resp = await client.put(
        f"/api/v1/blocks/{block['id']}", json={"name": "Renamed Block"}, headers=admin.headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Renamed Block"

    delete_resp = await client.delete(f"/api/v1/blocks/{block['id']}", headers=admin.headers)
    assert delete_resp.status_code == 204


async def test_block_nonexistent_district_returns_404(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    resp = await client.post(
        "/api/v1/blocks",
        json={"district_id": str(uuid.uuid4()), "name": "Ghost Block", "code": "GHOST"},
        headers=admin.headers,
    )
    assert resp.status_code == 404


async def test_block_duplicate_code_in_district_conflicts(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)
    payload = {"district_id": district["id"], "name": "Block A", "code": "SAME"}

    first = await client.post("/api/v1/blocks", json=payload, headers=admin.headers)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/blocks",
        json={"district_id": district["id"], "name": "Block B", "code": "SAME"},
        headers=admin.headers,
    )
    assert second.status_code == 409


async def test_village_crud_and_gps_validation(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)
    district = await _create_district(client, admin.headers)
    block = await _create_block(client, admin.headers, district["id"])

    bad_gps = await client.post(
        "/api/v1/villages",
        json={"block_id": block["id"], "name": "Bad Village", "latitude": 200.0},
        headers=admin.headers,
    )
    assert bad_gps.status_code == 422

    village = await _create_village(client, admin.headers, block["id"])

    get_resp = await client.get(f"/api/v1/villages/{village['id']}", headers=citizen.headers)
    assert get_resp.status_code == 200

    filter_resp = await client.get(
        f"/api/v1/villages?block_id={block['id']}", headers=admin.headers
    )
    assert filter_resp.status_code == 200
    assert filter_resp.json()["total"] == 1

    delete_forbidden = await client.delete(
        f"/api/v1/villages/{village['id']}", headers=citizen.headers
    )
    assert delete_forbidden.status_code == 403

    delete_resp = await client.delete(f"/api/v1/villages/{village['id']}", headers=admin.headers)
    assert delete_resp.status_code == 204


async def test_department_crud_rbac_and_duplicate(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)

    create_forbidden = await client.post(
        "/api/v1/departments", json={"name": "Cardiology"}, headers=citizen.headers
    )
    assert create_forbidden.status_code == 403

    department = await _create_department(client, admin.headers)

    duplicate = await client.post(
        "/api/v1/departments", json={"name": department["name"]}, headers=admin.headers
    )
    assert duplicate.status_code == 409

    list_resp = await client.get("/api/v1/departments", headers=citizen.headers)
    assert list_resp.status_code == 200

    update_resp = await client.put(
        f"/api/v1/departments/{department['id']}",
        json={"description": "Updated description"},
        headers=admin.headers,
    )
    assert update_resp.status_code == 200

    delete_resp = await client.delete(
        f"/api/v1/departments/{department['id']}", headers=admin.headers
    )
    assert delete_resp.status_code == 204


async def test_ward_crud_and_filters(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)
    district = await _create_district(client, admin.headers)
    centre = await _create_health_centre(client, admin.headers, district["id"])
    department = await _create_department(client, admin.headers)

    ward = await _create_ward(client, admin.headers, centre["id"], department["id"])

    filter_resp = await client.get(
        f"/api/v1/wards?health_centre_id={centre['id']}", headers=citizen.headers
    )
    assert filter_resp.status_code == 200
    assert filter_resp.json()["total"] == 1

    duplicate = await client.post(
        "/api/v1/wards",
        json={
            "health_centre_id": centre["id"],
            "department_id": department["id"],
            "name": ward["name"],
        },
        headers=admin.headers,
    )
    assert duplicate.status_code == 409

    delete_resp = await client.delete(f"/api/v1/wards/{ward['id']}", headers=admin.headers)
    assert delete_resp.status_code == 204


async def test_room_crud_and_filters(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)
    district = await _create_district(client, admin.headers)
    centre = await _create_health_centre(client, admin.headers, district["id"])
    department = await _create_department(client, admin.headers)
    ward = await _create_ward(client, admin.headers, centre["id"], department["id"])

    create_resp = await client.post(
        "/api/v1/rooms",
        json={"ward_id": ward["id"], "room_number": "101"},
        headers=admin.headers,
    )
    assert create_resp.status_code == 201
    room = create_resp.json()
    assert room["status"] == "available"

    filter_resp = await client.get(f"/api/v1/rooms?ward_id={ward['id']}", headers=citizen.headers)
    assert filter_resp.status_code == 200
    assert filter_resp.json()["total"] == 1

    duplicate = await client.post(
        "/api/v1/rooms",
        json={"ward_id": ward["id"], "room_number": "101"},
        headers=admin.headers,
    )
    assert duplicate.status_code == 409

    nonexistent_ward = await client.post(
        "/api/v1/rooms",
        json={"ward_id": str(uuid.uuid4()), "room_number": "202"},
        headers=admin.headers,
    )
    assert nonexistent_ward.status_code == 404

    delete_resp = await client.delete(f"/api/v1/rooms/{room['id']}", headers=admin.headers)
    assert delete_resp.status_code == 204


async def test_specialization_crud_and_rbac(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    citizen = await authed_client_factory(UserRole.CITIZEN)

    create_forbidden = await client.post(
        "/api/v1/specializations", json={"name": "Neurology"}, headers=citizen.headers
    )
    assert create_forbidden.status_code == 403

    create_resp = await client.post(
        "/api/v1/specializations", json={"name": "Neurology"}, headers=admin.headers
    )
    assert create_resp.status_code == 201
    specialization = create_resp.json()

    list_resp = await client.get("/api/v1/specializations", headers=citizen.headers)
    assert list_resp.status_code == 200

    duplicate = await client.post(
        "/api/v1/specializations", json={"name": "Neurology"}, headers=admin.headers
    )
    assert duplicate.status_code == 409

    delete_resp = await client.delete(
        f"/api/v1/specializations/{specialization['id']}", headers=admin.headers
    )
    assert delete_resp.status_code == 204


async def test_lookups_return_flat_lists(client, authed_client_factory):
    admin = await authed_client_factory(UserRole.SUPER_ADMIN)
    district = await _create_district(client, admin.headers)
    block = await _create_block(client, admin.headers, district["id"])
    await _create_village(client, admin.headers, block["id"])
    await _create_department(client, admin.headers)
    await _create_health_centre(client, admin.headers, district["id"])
    await client.post(
        "/api/v1/specializations",
        json={"name": f"Spec {uuid.uuid4().hex[:6]}"},
        headers=admin.headers,
    )

    for path in (
        "/api/v1/lookups/districts",
        f"/api/v1/lookups/blocks?district_id={district['id']}",
        f"/api/v1/lookups/villages?block_id={block['id']}",
        "/api/v1/lookups/health-centres",
        "/api/v1/lookups/departments",
        "/api/v1/lookups/specializations",
    ):
        resp = await client.get(path, headers=admin.headers)
        assert resp.status_code == 200, path
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert set(body[0].keys()) == {"id", "name"}


async def test_lookups_require_authentication(client):
    resp = await client.get("/api/v1/lookups/districts")
    assert resp.status_code == 401
