import uuid
from datetime import UTC, datetime

import pytest

from app.api.deps import require_roles
from app.core.exceptions import ForbiddenError
from app.models.user import User, UserRole, UserStatus


def _make_user(role: UserRole) -> User:
    return User(
        id=uuid.uuid4(),
        mobile_number="9000000000",
        country_code="+91",
        role=role,
        status=UserStatus.ACTIVE,
        is_verified=True,
        token_version=0,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.parametrize(
    "role",
    [
        UserRole.CITIZEN,
        UserRole.RECEPTION_STAFF,
        UserRole.DOCTOR,
        UserRole.PHARMACIST,
        UserRole.DISTRICT_ADMIN,
        UserRole.SUPER_ADMIN,
    ],
)
async def test_require_roles_allows_matching_role(role):
    dependency = require_roles(role)
    user = _make_user(role)
    result = await dependency(user=user)
    assert result is user


@pytest.mark.parametrize(
    "role",
    [
        UserRole.CITIZEN,
        UserRole.RECEPTION_STAFF,
        UserRole.DOCTOR,
        UserRole.PHARMACIST,
    ],
)
async def test_require_roles_rejects_non_admin(role):
    dependency = require_roles(UserRole.DISTRICT_ADMIN, UserRole.SUPER_ADMIN)
    user = _make_user(role)
    with pytest.raises(ForbiddenError) as exc_info:
        await dependency(user=user)
    assert exc_info.value.error_code == "forbidden"


async def test_require_roles_allows_either_of_multiple_roles():
    dependency = require_roles(UserRole.DOCTOR, UserRole.PHARMACIST)
    doctor = _make_user(UserRole.DOCTOR)
    pharmacist = _make_user(UserRole.PHARMACIST)
    assert await dependency(user=doctor) is doctor
    assert await dependency(user=pharmacist) is pharmacist
