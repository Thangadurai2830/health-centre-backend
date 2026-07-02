import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.health_centre import CentreStatus, CentreType
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.health_centre import (
    HealthCentreCreate,
    HealthCentreNearbyRead,
    HealthCentreRead,
    HealthCentreUpdate,
)
from app.services import health_centre_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[HealthCentreRead],
    summary="List health centres",
    description=(
        "Lists health centres, filterable by district_id/block_id/village_id/type/status "
        "and searchable by name, with sorting and pagination."
    ),
    tags=["health-centres"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_centres(
    district_id: uuid.UUID | None = None,
    block_id: uuid.UUID | None = None,
    village_id: uuid.UUID | None = None,
    type: CentreType | None = None,
    status_: CentreStatus | None = Query(default=None, alias="status"),
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[HealthCentreRead]:
    centres, total = await health_centre_service.list_health_centres(
        db,
        district_id=district_id,
        block_id=block_id,
        village_id=village_id,
        type=type,
        status=status_,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[HealthCentreRead.model_validate(c) for c in centres],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/nearby",
    response_model=list[HealthCentreNearbyRead],
    summary="Find nearby health centres",
    description=(
        "Returns active health centres with known coordinates within radius_km of the given "
        "lat/lng, sorted by ascending distance. NOTE: this route is registered before "
        "/{centre_id} so 'nearby' is not mistaken for a path parameter."
    ),
    tags=["health-centres"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        422: {"model": ErrorResponse, "description": "Invalid lat/lng/radius_km parameters"},
    },
)
async def list_nearby_centres(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10, gt=0),
    limit: int = Query(20, le=200),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[HealthCentreNearbyRead]:
    nearby = await health_centre_service.list_nearby(
        db, lat=lat, lng=lng, radius_km=radius_km, limit=limit
    )
    return [
        HealthCentreNearbyRead.model_validate(
            {**HealthCentreRead.model_validate(centre).model_dump(), "distance_km": distance}
        )
        for centre, distance in nearby
    ]


@router.post(
    "",
    response_model=HealthCentreRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a health centre",
    description=(
        "Creates a new health centre under a district (and optionally a block/village). "
        "Name must be unique within the district."
    ),
    tags=["health-centres"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "District, block, or village not found"},
        409: {
            "model": ErrorResponse,
            "description": "Health centre name already exists in district",
        },
        422: {
            "model": ErrorResponse,
            "description": "Invalid request body (e.g. bad GPS coords or phone format)",
        },
    },
)
async def create_centre(
    payload: HealthCentreCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> HealthCentreRead:
    centre = await health_centre_service.create_health_centre(db, payload)
    return HealthCentreRead.model_validate(centre)


@router.get(
    "/{centre_id}",
    response_model=HealthCentreRead,
    summary="Get a health centre",
    description="Fetches a single health centre by id.",
    tags=["health-centres"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "Health centre not found"},
    },
)
async def get_centre(
    centre_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> HealthCentreRead:
    centre = await health_centre_service.get_health_centre(db, centre_id)
    return HealthCentreRead.model_validate(centre)


@router.put(
    "/{centre_id}",
    response_model=HealthCentreRead,
    summary="Update a health centre",
    description="Partially updates a health centre's fields.",
    tags=["health-centres"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Health centre, block, or village not found"},
        409: {
            "model": ErrorResponse,
            "description": "Health centre name already exists in district",
        },
        422: {
            "model": ErrorResponse,
            "description": "Invalid request body (e.g. bad GPS coords or phone format)",
        },
    },
)
async def update_centre(
    centre_id: uuid.UUID,
    payload: HealthCentreUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> HealthCentreRead:
    centre = await health_centre_service.update_health_centre(db, centre_id, payload)
    return HealthCentreRead.model_validate(centre)


@router.delete(
    "/{centre_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a health centre",
    description="Deletes a health centre. Fails if other records still reference it.",
    tags=["health-centres"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Health centre not found"},
        409: {
            "model": ErrorResponse,
            "description": "Health centre is referenced by other records",
        },
    },
)
async def delete_centre(
    centre_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await health_centre_service.delete_health_centre(db, centre_id)
