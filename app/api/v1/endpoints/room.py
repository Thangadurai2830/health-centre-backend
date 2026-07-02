import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.room import RoomCreate, RoomRead, RoomUpdate
from app.services import room_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[RoomRead],
    summary="List rooms",
    description="Lists rooms, filterable by ward_id, with search and pagination.",
    tags=["rooms"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_rooms(
    ward_id: uuid.UUID | None = None,
    search: str | None = None,
    sort_by: str = "room_number",
    sort_order: str = "asc",
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[RoomRead]:
    rooms, total = await room_service.list_rooms(
        db,
        ward_id=ward_id,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[RoomRead.model_validate(r) for r in rooms], total=total, limit=limit, offset=offset
    )


@router.post(
    "",
    response_model=RoomRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a room",
    description="Creates a new room under a ward. The (ward_id, room_number) pair must be unique.",
    tags=["rooms"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Ward not found"},
        409: {"model": ErrorResponse, "description": "Room number already exists in this ward"},
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def create_room(
    payload: RoomCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> RoomRead:
    room = await room_service.create_room(db, payload)
    return RoomRead.model_validate(room)


@router.get(
    "/{room_id}",
    response_model=RoomRead,
    summary="Get a room",
    description="Fetches a single room by id.",
    tags=["rooms"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "Room not found"},
    },
)
async def get_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> RoomRead:
    room = await room_service.get_room(db, room_id)
    return RoomRead.model_validate(room)


@router.put(
    "/{room_id}",
    response_model=RoomRead,
    summary="Update a room",
    description="Partially updates a room's fields.",
    tags=["rooms"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Room not found"},
        409: {"model": ErrorResponse, "description": "Room number already exists in this ward"},
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def update_room(
    room_id: uuid.UUID,
    payload: RoomUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> RoomRead:
    room = await room_service.update_room(db, room_id, payload)
    return RoomRead.model_validate(room)


@router.delete(
    "/{room_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a room",
    description="Deletes a room.",
    tags=["rooms"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Room not found"},
        409: {"model": ErrorResponse, "description": "Room is referenced by other records"},
    },
)
async def delete_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await room_service.delete_room(db, room_id)
