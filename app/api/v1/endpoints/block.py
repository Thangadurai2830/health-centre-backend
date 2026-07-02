import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.user import User, UserRole
from app.schemas.block import BlockCreate, BlockRead, BlockUpdate
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.services import block_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[BlockRead],
    summary="List blocks",
    description=(
        "Lists blocks with pagination, name search, sorting, and optional district_id filter."
    ),
    tags=["blocks"],
    responses={401: {"model": ErrorResponse, "description": "Missing or invalid access token"}},
)
async def list_blocks(
    district_id: uuid.UUID | None = None,
    search: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("name"),
    sort_order: str = Query("asc"),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[BlockRead]:
    items, total = await block_service.list_blocks(
        db,
        district_id=district_id,
        search=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PaginatedResponse(
        items=[BlockRead.model_validate(i) for i in items], total=total, limit=limit, offset=offset
    )


@router.post(
    "",
    response_model=BlockRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create block",
    description=(
        "Creates a new block under a district. Requires district admin or super admin role."
    ),
    tags=["blocks"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Insufficient role"},
        404: {"model": ErrorResponse, "description": "District not found"},
        409: {"model": ErrorResponse, "description": "Block code already exists in district"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_block(
    payload: BlockCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> BlockRead:
    block = await block_service.create_block(db, payload)
    return BlockRead.model_validate(block)


@router.get(
    "/{block_id}",
    response_model=BlockRead,
    summary="Get block",
    description="Fetches a single block by id.",
    tags=["blocks"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "Block not found"},
    },
)
async def get_block(
    block_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> BlockRead:
    block = await block_service.get_block(db, block_id)
    return BlockRead.model_validate(block)


@router.put(
    "/{block_id}",
    response_model=BlockRead,
    summary="Update block",
    description="Partially updates a block. Requires district admin or super admin role.",
    tags=["blocks"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Insufficient role"},
        404: {"model": ErrorResponse, "description": "Block not found"},
        409: {"model": ErrorResponse, "description": "Block code already exists in district"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_block(
    block_id: uuid.UUID,
    payload: BlockUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> BlockRead:
    block = await block_service.update_block(db, block_id, payload)
    return BlockRead.model_validate(block)


@router.delete(
    "/{block_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete block",
    description="Deletes a block. Requires district admin or super admin role.",
    tags=["blocks"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Insufficient role"},
        404: {"model": ErrorResponse, "description": "Block not found"},
        409: {"model": ErrorResponse, "description": "Block is referenced by other records"},
    },
)
async def delete_block(
    block_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await block_service.delete_block(db, block_id)
