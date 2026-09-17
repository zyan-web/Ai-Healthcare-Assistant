"""
Shared contracts every tool follows.

Rule (project docs, section 5 / 31): the LLM only ever sees the result of
`ToolResponse` — it never gets raw exceptions, stack traces, or direct
database/API access. Deterministic code decides success/failure; the tool
never claims success without one.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolErrorCode(str, Enum):
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    CONFLICT = "CONFLICT"
    UNAUTHORIZED = "UNAUTHORIZED"
    UPSTREAM_UNAVAILABLE = "UPSTREAM_UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"


class ToolError(BaseModel):
    code: ToolErrorCode
    message: str


class ToolResponse(BaseModel, Generic[T]):
    """Every tool returns exactly this envelope — never a bare value and
    never a raised exception the LLM would have to interpret."""

    success: bool
    data: Optional[T] = None
    error: Optional[ToolError] = None

    @classmethod
    def ok(cls, data: T) -> "ToolResponse[T]":
        return cls(success=True, data=data, error=None)

    @classmethod
    def fail(cls, code: ToolErrorCode, message: str) -> "ToolResponse[T]":
        return cls(success=False, data=None, error=ToolError(code=code, message=message))


class AppointmentStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class Role(str, Enum):
    PATIENT = "PATIENT"
    RECEPTIONIST = "RECEPTIONIST"
    BILLING = "BILLING"
    ADMIN = "ADMIN"


class DataScope(str, Enum):
    OWN_DATA = "OWN_DATA"
    ASSIGNED_DATA = "ASSIGNED_DATA"
    DEPARTMENT_DATA = "DEPARTMENT_DATA"
    ALL_DATA = "ALL_DATA"


class ActorContext(BaseModel):
    """Trusted caller identity, passed into every tool.

    In Stage A this is constructed directly by tests/the graph. In Stage B
    it is populated from the JWT by FastAPI and is never something the LLM
    can set itself (section 17).
    """

    user_id: str
    role: Role
    scope: DataScope = DataScope.OWN_DATA
    extra: dict[str, Any] = Field(default_factory=dict)
