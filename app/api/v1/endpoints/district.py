import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.district import DistrictCreate, DistrictRead, DistrictUpdate
from app.services import district_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[DistrictRead],
    summary="List districts",
    description="Lists districts with pagination, name search, and sorting.",
    tags=["districts"],
    responses={401: {"model": ErrorResponse, "description": "Missing or invalid access token"}},
)
async def list_districts(
    search: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[DistrictRead]:
    items, total = await district_service.list_districts(
        db, search=search, limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
    )
    return PaginatedResponse(
        items=[DistrictRead.model_validate(i) for i in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=DistrictRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create district",
    description="Creates a new district. Requires district admin or super admin role.",
    tags=["districts"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Insufficient role"},
        409: {"model": ErrorResponse, "description": "District code already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_district(
    payload: DistrictCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> DistrictRead:
    district = await district_service.create_district(db, payload)
    return DistrictRead.model_validate(district)


@router.get(
    "/{district_id}",
    response_model=DistrictRead,
    summary="Get district",
    description="Fetches a single district by id.",
    tags=["districts"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "District not found"},
    },
)
async def get_district(
    district_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> DistrictRead:
    district = await district_service.get_district(db, district_id)
    return DistrictRead.model_validate(district)


@router.put(
    "/{district_id}",
    response_model=DistrictRead,
    summary="Update district",
    description="Partially updates a district. Requires district admin or super admin role.",
    tags=["districts"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Insufficient role"},
        404: {"model": ErrorResponse, "description": "District not found"},
        409: {"model": ErrorResponse, "description": "District code already exists"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_district(
    district_id: uuid.UUID,
    payload: DistrictUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> DistrictRead:
    district = await district_service.update_district(db, district_id, payload)
    return DistrictRead.model_validate(district)


@router.delete(
    "/{district_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete district",
    description="Deletes a district. Requires district admin or super admin role.",
    tags=["districts"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Insufficient role"},
        404: {"model": ErrorResponse, "description": "District not found"},
        409: {"model": ErrorResponse, "description": "District is referenced by other records"},
    },
)
async def delete_district(
    district_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await district_service.delete_district(db, district_id)
