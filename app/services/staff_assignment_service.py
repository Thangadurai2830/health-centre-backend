import uuid
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models.department import Department
from app.models.health_centre import HealthCentre
from app.models.staff_assignment import AssignmentStatus, StaffAssignment
from app.models.user import User
from app.schemas.staff_assignment import StaffAssignmentCreate, StaffTransferRequest


async def _ensure_user_exists(db: AsyncSession, user_id: uuid.UUID) -> None:
    user = await db.get(User, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")


async def _ensure_health_centre_exists(db: AsyncSession, health_centre_id: uuid.UUID) -> None:
    centre = await db.get(HealthCentre, health_centre_id)
    if centre is None:
        raise NotFoundError(f"Health centre {health_centre_id} not found")


async def _ensure_department_exists(db: AsyncSession, department_id: uuid.UUID) -> None:
    department = await db.get(Department, department_id)
    if department is None:
        raise NotFoundError(f"Department {department_id} not found")


async def _get_active_assignment(db: AsyncSession, user_id: uuid.UUID) -> StaffAssignment | None:
    stmt = select(StaffAssignment).where(
        StaffAssignment.user_id == user_id, StaffAssignment.status == AssignmentStatus.ACTIVE
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def assign_staff(db: AsyncSession, payload: StaffAssignmentCreate) -> StaffAssignment:
    await _ensure_user_exists(db, payload.user_id)
    await _ensure_health_centre_exists(db, payload.health_centre_id)
    if payload.department_id is not None:
        await _ensure_department_exists(db, payload.department_id)

    existing = await _get_active_assignment(db, payload.user_id)
    if existing is not None:
        raise ConflictError("User already has an active staff assignment")

    assignment = StaffAssignment(
        user_id=payload.user_id,
        health_centre_id=payload.health_centre_id,
        department_id=payload.department_id,
        designation=payload.designation,
        joined_date=payload.joined_date or date.today(),
        status=AssignmentStatus.ACTIVE,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment


async def transfer_staff(db: AsyncSession, payload: StaffTransferRequest) -> StaffAssignment:
    current = await _get_active_assignment(db, payload.user_id)
    if current is None:
        raise NotFoundError("User has no active assignment to transfer")

    await _ensure_health_centre_exists(db, payload.health_centre_id)
    if payload.department_id is not None:
        await _ensure_department_exists(db, payload.department_id)

    current.status = AssignmentStatus.TRANSFERRED
    # Flush the UPDATE before adding the new ACTIVE row: the partial unique index
    # `ux_staff_assignments_one_active_per_user` would otherwise reject the INSERT if
    # SQLAlchemy happened to emit it before the UPDATE within the same flush (unrelated
    # objects have no ordering guarantee). Both statements still commit atomically below.
    await db.flush()

    new_assignment = StaffAssignment(
        user_id=payload.user_id,
        health_centre_id=payload.health_centre_id,
        department_id=payload.department_id,
        designation=payload.designation,
        joined_date=payload.joined_date or date.today(),
        status=AssignmentStatus.ACTIVE,
    )
    db.add(new_assignment)

    await db.commit()
    await db.refresh(new_assignment)
    return new_assignment


async def list_staff_for_health_centre(
    db: AsyncSession,
    health_centre_id: uuid.UUID,
    *,
    status: AssignmentStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[StaffAssignment], int]:
    stmt = select(StaffAssignment).where(StaffAssignment.health_centre_id == health_centre_id)
    count_stmt = (
        select(func.count())
        .select_from(StaffAssignment)
        .where(StaffAssignment.health_centre_id == health_centre_id)
    )
    if status is not None:
        stmt = stmt.where(StaffAssignment.status == status)
        count_stmt = count_stmt.where(StaffAssignment.status == status)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(StaffAssignment.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all()), total
