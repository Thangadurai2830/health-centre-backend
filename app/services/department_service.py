import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError, ValidationAppError
from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate

SORTABLE_COLUMNS = {"name": Department.name, "created_at": Department.created_at}


async def list_departments(
    db: AsyncSession,
    *,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "name",
    sort_order: str = "asc",
) -> tuple[list[Department], int]:
    if sort_by not in SORTABLE_COLUMNS:
        raise ValidationAppError(f"sort_by must be one of {sorted(SORTABLE_COLUMNS)}")
    if sort_order not in {"asc", "desc"}:
        raise ValidationAppError("sort_order must be 'asc' or 'desc'")

    column = SORTABLE_COLUMNS[sort_by]
    order = column.asc() if sort_order == "asc" else column.desc()

    stmt = select(Department)
    count_stmt = select(func.count()).select_from(Department)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Department.name.ilike(pattern))
        count_stmt = count_stmt.where(Department.name.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(order).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total


async def get_department(db: AsyncSession, department_id: uuid.UUID) -> Department:
    department = await db.get(Department, department_id)
    if department is None:
        raise NotFoundError(f"Department {department_id} not found")
    return department


async def _check_duplicate_name(
    db: AsyncSession, name: str, *, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = select(Department).where(Department.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Department.id != exclude_id)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ConflictError(f"Department '{name}' already exists")


async def create_department(db: AsyncSession, payload: DepartmentCreate) -> Department:
    await _check_duplicate_name(db, payload.name)
    department = Department(**payload.model_dump())
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return department


async def update_department(
    db: AsyncSession, department_id: uuid.UUID, payload: DepartmentUpdate
) -> Department:
    department = await get_department(db, department_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != department.name:
        await _check_duplicate_name(db, data["name"], exclude_id=department_id)
    for field, value in data.items():
        setattr(department, field, value)
    await db.commit()
    await db.refresh(department)
    return department


async def delete_department(db: AsyncSession, department_id: uuid.UUID) -> None:
    department = await get_department(db, department_id)
    await db.delete(department)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("Cannot delete department because other records reference it") from exc
