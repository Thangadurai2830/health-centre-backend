import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_session, require_roles
from app.models.user import User, UserRole
from app.schemas.common import ErrorResponse, PaginatedResponse
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate
from app.services import department_service

router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[DepartmentRead],
    summary="List departments",
    description="Lists the global department catalog with search, sorting, and pagination.",
    tags=["departments"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
    },
)
async def list_departments(
    search: str | None = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> PaginatedResponse[DepartmentRead]:
    departments, total = await department_service.list_departments(
        db, search=search, limit=limit, offset=offset, sort_by=sort_by, sort_order=sort_order
    )
    return PaginatedResponse(
        items=[DepartmentRead.model_validate(d) for d in departments],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department",
    description="Creates a new department in the global catalog. Name must be unique.",
    tags=["departments"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        409: {"model": ErrorResponse, "description": "Department name already exists"},
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def create_department(
    payload: DepartmentCreate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> DepartmentRead:
    department = await department_service.create_department(db, payload)
    return DepartmentRead.model_validate(department)


@router.get(
    "/{department_id}",
    response_model=DepartmentRead,
    summary="Get a department",
    description="Fetches a single department by id.",
    tags=["departments"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        404: {"model": ErrorResponse, "description": "Department not found"},
    },
)
async def get_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(get_current_user),
) -> DepartmentRead:
    department = await department_service.get_department(db, department_id)
    return DepartmentRead.model_validate(department)


@router.put(
    "/{department_id}",
    response_model=DepartmentRead,
    summary="Update a department",
    description="Partially updates a department's fields.",
    tags=["departments"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Department not found"},
        409: {"model": ErrorResponse, "description": "Department name already exists"},
        422: {"model": ErrorResponse, "description": "Invalid request body"},
    },
)
async def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> DepartmentRead:
    department = await department_service.update_department(db, department_id, payload)
    return DepartmentRead.model_validate(department)


@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department",
    description="Deletes a department. Fails if other records still reference it.",
    tags=["departments"],
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid access token"},
        403: {"model": ErrorResponse, "description": "Caller is not an admin"},
        404: {"model": ErrorResponse, "description": "Department not found"},
        409: {"model": ErrorResponse, "description": "Department is referenced by other records"},
    },
)
async def delete_department(
    department_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    _user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.DISTRICT_ADMIN)),
) -> None:
    await department_service.delete_department(db, department_id)
