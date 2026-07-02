import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.ward import WardCreate, WardRead, WardUpdate
from app.services import ward_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[WardRead],
    summary="List wards",
    description=(
        "Lists wards, filterable by health_centre_id/department_id, with search and pagination."
    ),
    tags=["wards"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_wards(
    health_centre_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[WardRead]:
    wards, total = await ward_service.list_wards(
        db,
        health_centre_id=health_centre_id,
        department_id=department_id,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[WardRead.model_validate(w) for w in wards], total=total, limit=limit, offset=offset
    )


@router.post(
    "",
    response_model=WardRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ward",
    description="Creates a new ward tying a department to a specific health centre.",
    tags=["wards"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Health centre or department not found"},
        409: {
            "model": ErrorResponse,
            "description": "Ward name already exists in this health centre",
        },
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def create_ward(
    payload: WardCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> WardRead:
    ward = await ward_service.create_ward(db, payload)
    return WardRead.model_validate(ward)


@router.get(
    "/{ward_id}",
    response_model=WardRead,
    summary="Get a ward",
    description="Fetches a single ward by id.",
    tags=["wards"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "Ward not found"},
    },
)
async def get_ward(
    ward_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> WardRead:
    ward = await ward_service.get_ward(db, ward_id)
    return WardRead.model_validate(ward)


@router.put(
    "/{ward_id}",
    response_model=WardRead,
    summary="Update a ward",
    description="Partially updates a ward's fields.",
    tags=["wards"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Ward or department not found"},
        409: {
            "model": ErrorResponse,
            "description": "Ward name already exists in this health centre",
        },
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def update_ward(
    ward_id: uuid.UUID,
    payload: WardUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> WardRead:
    ward = await ward_service.update_ward(db, ward_id, payload)
    return WardRead.model_validate(ward)


@router.delete(
    "/{ward_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ward",
    description="Deletes a ward. Fails if other records still reference it.",
    tags=["wards"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Ward not found"},
        409: {"model": ErrorResponse, "description": "Ward is referenced by other records"},
    },
)
async def delete_ward(
    ward_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await ward_service.delete_ward(db, ward_id)
