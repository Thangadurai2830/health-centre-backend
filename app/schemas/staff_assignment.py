import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict

from app.models.staff_assignment import AssignmentStatus


class StaffAssignmentCreate(BaseModel):
    user_id: uuid.UUID
    health_centre_id: uuid.UUID
    department_id: uuid.UUID | None = None
    designation: str | None = None
    joined_date: date | None = None


class StaffTransferRequest(BaseModel):
    user_id: uuid.UUID
    health_centre_id: uuid.UUID
    department_id: uuid.UUID | None = None
    designation: str | None = None
    joined_date: date | None = None


class StaffAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    health_centre_id: uuid.UUID
    department_id: uuid.UUID | None
    designation: str | None
    joined_date: date | None
    status: AssignmentStatus
