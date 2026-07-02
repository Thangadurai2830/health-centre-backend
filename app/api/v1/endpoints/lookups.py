import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session
from app.models.block import Block
from app.models.department import Department
from app.models.district import District
from app.models.health_centre import HealthCentre
from app.models.specialization import Specialization
from app.models.user import User
from app.models.village import Village
from app.schemas.common import ErrorResponse
from app.schemas.lookup import LookupItem

router = APIRouter()

LOOKUP_CAP = 500


@router.get(
    "/districts",
    response_model=list[LookupItem],
    summary="Lookup: districts",
    description="Flat list of {id, name} for all districts, capped at 500 results.",
    tags=["lookups"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def lookup_districts(
    db: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> list[LookupItem]:
    stmt = select(District).order_by(District.name).limit(LOOKUP_CAP)
    result = await db.execute(stmt)
    return [LookupItem.model_validate(d) for d in result.scalars().all()]


@router.get(
    "/blocks",
    response_model=list[LookupItem],
    summary="Lookup: blocks",
    description=(
        "Flat list of {id, name} for blocks, optionally filtered by district_id, "
        "capped at 500 results."
    ),
    tags=["lookups"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def lookup_blocks(
    district_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[LookupItem]:
    stmt = select(Block).order_by(Block.name).limit(LOOKUP_CAP)
    if district_id is not None:
        stmt = stmt.where(Block.district_id == district_id)
    result = await db.execute(stmt)
    return [LookupItem.model_validate(b) for b in result.scalars().all()]


@router.get(
    "/villages",
    response_model=list[LookupItem],
    summary="Lookup: villages",
    description=(
        "Flat list of {id, name} for villages, optionally filtered by block_id, "
        "capped at 500 results."
    ),
    tags=["lookups"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def lookup_villages(
    block_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> list[LookupItem]:
    stmt = select(Village).order_by(Village.name).limit(LOOKUP_CAP)
    if block_id is not None:
        stmt = stmt.where(Village.block_id == block_id)
    result = await db.execute(stmt)
    return [LookupItem.model_validate(v) for v in result.scalars().all()]


@router.get(
    "/health-centres",
    response_model=list[LookupItem],
    summary="Lookup: health centres",
    description="Flat list of {id, name} for health centres, capped at 500 results.",
    tags=["lookups"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def lookup_health_centres(
    db: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> list[LookupItem]:
    stmt = select(HealthCentre).order_by(HealthCentre.name).limit(LOOKUP_CAP)
    result = await db.execute(stmt)
    return [LookupItem.model_validate(c) for c in result.scalars().all()]


@router.get(
    "/departments",
    response_model=list[LookupItem],
    summary="Lookup: departments",
    description="Flat list of {id, name} for departments, capped at 500 results.",
    tags=["lookups"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def lookup_departments(
    db: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> list[LookupItem]:
    stmt = select(Department).order_by(Department.name).limit(LOOKUP_CAP)
    result = await db.execute(stmt)
    return [LookupItem.model_validate(d) for d in result.scalars().all()]


@router.get(
    "/specializations",
    response_model=list[LookupItem],
    summary="Lookup: specializations",
    description="Flat list of {id, name} for specializations, capped at 500 results.",
    tags=["lookups"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def lookup_specializations(
    db: AsyncSession = Depends(get_session), _user: User = Depends(get_current_user)
) -> list[LookupItem]:
    stmt = select(Specialization).order_by(Specialization.name).limit(LOOKUP_CAP)
    result = await db.execute(stmt)
    return [LookupItem.model_validate(s) for s in result.scalars().all()]
