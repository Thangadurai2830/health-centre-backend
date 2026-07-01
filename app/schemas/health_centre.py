import uuid

from pydantic import BaseModel, ConfigDict

from app.models.health_centre import CentreStatus, CentreType


class HealthCentreBase(BaseModel):
    name: str
    type: CentreType
    lat: float
    lng: float
    catchment_population: int = 0
    bed_capacity: int = 0


class HealthCentreCreate(HealthCentreBase):
    district_id: uuid.UUID


class HealthCentreUpdate(BaseModel):
    name: str | None = None
    bed_capacity: int | None = None
    status: CentreStatus | None = None


class HealthCentreRead(HealthCentreBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    district_id: uuid.UUID
    performance_score: float
    status: CentreStatus
