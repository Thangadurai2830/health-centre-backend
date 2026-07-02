import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.specialization import (
    SpecializationCreate,
    SpecializationRead,
    SpecializationUpdate,
)
from app.services import specialization_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[SpecializationRead],
    summary="List specializations",
    description="Lists the specialization catalog with search, sorting, and pagination.",
    tags=["specializations"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_specializations(
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[SpecializationRead]:
    specializations, total = await specialization_service.list_specializations(
        db, search=search, limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
    )
    return PaginatedResponse(
        items=[SpecializationRead.model_validate(s) for s in specializations],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=SpecializationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a specialization",
    description="Creates a new specialization. Name must be unique.",
    tags=["specializations"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        409: {"model": ErrorResponse, "description": "Specialization name already exists"},
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def create_specialization(
    payload: SpecializationCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> SpecializationRead:
    specialization = await specialization_service.create_specialization(db, payload)
    return SpecializationRead.model_validate(specialization)


@router.get(
    "/{specialization_id}",
    response_model=SpecializationRead,
    summary="Get a specialization",
    description="Fetches a single specialization by id.",
    tags=["specializations"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "Specialization not found"},
    },
)
async def get_specialization(
    specialization_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> SpecializationRead:
    specialization = await specialization_service.get_specialization(db, specialization_id)
    return SpecializationRead.model_validate(specialization)


@router.put(
    "/{specialization_id}",
    response_model=SpecializationRead,
    summary="Update a specialization",
    description="Partially updates a specialization's fields.",
    tags=["specializations"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Specialization not found"},
        409: {"model": ErrorResponse, "description": "Specialization name already exists"},
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def update_specialization(
    specialization_id: uuid.UUID,
    payload: SpecializationUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> SpecializationRead:
    specialization = await specialization_service.update_specialization(
        db, specialization_id, payload
    )
    return SpecializationRead.model_validate(specialization)


@router.delete(
    "/{specialization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a specialization",
    description="Deletes a specialization. Fails if other records still reference it.",
    tags=["specializations"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Specialization not found"},
        409: {
            "model": ErrorResponse,
            "description": "Specialization is referenced by other records",
        },
    },
)
async def delete_specialization(
    specialization_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await specialization_service.delete_specialization(db, specialization_id)
