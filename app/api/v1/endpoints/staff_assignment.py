import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.staff_assignment import AssignmentStatus
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.staff_assignment import (
    StaffAssignmentCreate,
    StaffAssignmentRead,
    StaffTransferRequest,
)
from app.services import staff_assignment_service

router = APIRouter()


@router.post(
    "/assign",
    response_model=StaffAssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign staff to a health centre",
    description=(
        "Creates a new ACTIVE staff assignment for a user at a health centre. A user may have "
        "at most one ACTIVE assignment at a time."
    ),
    tags=["staff"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {
            "model": ErrorResponse,
            "description": "User, health centre, or department not found",
        },
        409: {"model": ErrorResponse, "description": "User already has an active assignment"},
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def assign_staff(
    payload: StaffAssignmentCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> StaffAssignmentRead:
    assignment = await staff_assignment_service.assign_staff(db, payload)
    return StaffAssignmentRead.model_validate(assignment)


@router.put(
    "/transfer",
    response_model=StaffAssignmentRead,
    summary="Transfer staff to a different health centre",
    description=(
        "Marks the user's current ACTIVE assignment as TRANSFERRED and creates a new ACTIVE "
        "assignment at the target health centre, atomically."
    ),
    tags=["staff"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {
            "model": ErrorResponse,
            "description": (
                "User has no active assignment to transfer, or health centre/department not found"
            ),
        },
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def transfer_staff(
    payload: StaffTransferRequest,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> StaffAssignmentRead:
    assignment = await staff_assignment_service.transfer_staff(db, payload)
    return StaffAssignmentRead.model_validate(assignment)


@router.get(
    "/health-centre/{health_centre_id}",
    response_model=PaginatedResponse[StaffAssignmentRead],
    summary="List staff assignments for a health centre",
    description="Lists staff assignments for a health centre, optionally filtered by status.",
    tags=["staff"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_staff_for_health_centre(
    health_centre_id: uuid.UUID,
    status_: AssignmentStatus | None = Query(default=None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[StaffAssignmentRead]:
    assignments, total = await staff_assignment_service.list_staff_for_health_centre(
        db, health_centre_id, status=status_, limit=limit, offset=offset
    )
    return PaginatedResponse(
        items=[StaffAssignmentRead.model_validate(a) for a in assignments],
        total=total,
        limit=limit,
        offset=offset,
    )
