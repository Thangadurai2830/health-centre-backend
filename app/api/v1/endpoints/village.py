import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.village import VillageCreate, VillageRead, VillageUpdate
from app.services import village_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[VillageRead],
    summary="List villages",
    description="Lists villages, optionally filtered by block_id, with search and pagination.",
    tags=["villages"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_villages(
    block_id: uuid.UUID | None = None,
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[VillageRead]:
    villages, total = await village_service.list_villages(
        db,
        block_id=block_id,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[VillageRead.model_validate(v) for v in villages],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=VillageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a village",
    description="Creates a new village under a block.",
    tags=["villages"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Block not found"},
        422: {"model": ErrorResponse, "description": "Invalid request body (e.g. bad GPS coords)"},
    },
)
async def create_village(
    payload: VillageCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> VillageRead:
    village = await village_service.create_village(db, payload)
    return VillageRead.model_validate(village)


@router.get(
    "/{village_id}",
    response_model=VillageRead,
    summary="Get a village",
    description="Fetches a single village by id.",
    tags=["villages"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "Village not found"},
    },
)
async def get_village(
    village_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> VillageRead:
    village = await village_service.get_village(db, village_id)
    return VillageRead.model_validate(village)


@router.put(
    "/{village_id}",
    response_model=VillageRead,
    summary="Update a village",
    description="Partially updates a village's fields.",
    tags=["villages"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Village not found"},
        422: {"model": ErrorResponse, "description": "Invalid request body (e.g. bad GPS coords)"},
    },
)
async def update_village(
    village_id: uuid.UUID,
    payload: VillageUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> VillageRead:
    village = await village_service.update_village(db, village_id, payload)
    return VillageRead.model_validate(village)


@router.delete(
    "/{village_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a village",
    description="Deletes a village. Fails if other records still reference it.",
    tags=["villages"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Village not found"},
        409: {"model": ErrorResponse, "description": "Village is referenced by other records"},
    },
)
async def delete_village(
    village_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await village_service.delete_village(db, village_id)
