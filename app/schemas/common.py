from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class HealthCheckResponse(BaseModel):
    status: str = Field(default="ok", examples=["ok"])
    environment: str = Field(examples=["local"])


class DependencyHealthResponse(BaseModel):
    status: str = Field(examples=["ok"])
    detail: str | None = Field(default=None, examples=[None])


class ReadinessResponse(BaseModel):
    status: str = Field(examples=["ready"])
    checks: dict[str, str] = Field(examples=[{"database": "ok", "redis": "ok"}])


class LivenessResponse(BaseModel):
    status: str = Field(default="alive", examples=["alive"])


class VersionResponse(BaseModel):
    name: str = Field(examples=["SwasthyaSetu API"])
    version: str = Field(examples=["0.1.0"])
    environment: str = Field(examples=["local"])


class RootResponse(BaseModel):
    name: str = Field(examples=["SwasthyaSetu API"])
    status: str = Field(default="ok", examples=["ok"])
    docs_url: str | None = Field(default=None, examples=["/docs"])


class ErrorResponse(BaseModel):
    error_code: str
    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
