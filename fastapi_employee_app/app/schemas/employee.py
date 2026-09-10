"""
app/schemas/employee.py

Pydantic v2 schemas for creating, updating, and returning employee data.
"""

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

PHONE_REGEX = re.compile(r"^\+?[0-9]{7,15}$")


class EmployeeBase(BaseModel):
    """Fields shared between create and update schemas."""

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    age: int = Field(ge=18, le=100, description="Employee age, must be a working adult")
    gender: str = Field(min_length=1, max_length=20)
    department: str = Field(min_length=1, max_length=100)
    designation: str = Field(min_length=1, max_length=100)
    salary: float = Field(gt=0, description="Must be a positive number")
    joining_date: date
    address: str = Field(min_length=1, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        """Ensure phone is digits only (optionally with a leading '+'), 7-15 digits long."""
        if not PHONE_REGEX.match(value):
            raise ValueError("Phone number must contain 7-15 digits, optionally prefixed with '+'")
        return value

    @field_validator("joining_date")
    @classmethod
    def joining_date_not_in_future(cls, value: date) -> date:
        """Prevent nonsensical joining dates far in the future."""
        if value > date.today().replace(year=date.today().year + 1):
            raise ValueError("Joining date cannot be more than a year in the future")
        return value


class EmployeeCreate(EmployeeBase):
    """Request body for POST /employees."""

    pass


class EmployeeUpdate(BaseModel):
    """
    Request body for PUT /employees/{employee_id}.

    All fields are optional here (unlike EmployeeCreate) so a client can
    submit a partial update -- only the fields provided will be changed.
    """

    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    age: int | None = Field(default=None, ge=18, le=100)
    gender: str | None = Field(default=None, min_length=1, max_length=20)
    department: str | None = Field(default=None, min_length=1, max_length=100)
    designation: str | None = Field(default=None, min_length=1, max_length=100)
    salary: float | None = Field(default=None, gt=0)
    joining_date: date | None = None
    address: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    state: str | None = Field(default=None, min_length=1, max_length=100)
    country: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is not None and not PHONE_REGEX.match(value):
            raise ValueError("Phone number must contain 7-15 digits, optionally prefixed with '+'")
        return value


class EmployeeResponse(EmployeeBase):
    """Response body shape returned by all employee endpoints."""

    employee_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EmployeeListResponse(BaseModel):
    """Paginated list response wrapper for GET /employees."""

    total: int
    page: int
    limit: int
    items: list[EmployeeResponse]
