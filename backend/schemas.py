from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

class LoginBody(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)

class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=12, max_length=128)

class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    full_name: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=80)
    pin: str = Field(min_length=4, max_length=12, pattern=r"^\d+$")

class EmployeePatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    department: str | None = Field(default=None, min_length=2, max_length=80)
    active: bool | None = None
    model_config = ConfigDict(extra="forbid")

class PinReset(BaseModel):
    pin: str = Field(min_length=4, max_length=12, pattern=r"^\d+$")

class DeviceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=120)

class PairBody(BaseModel):
    code: str = Field(min_length=8, max_length=128)

class AttendanceBody(BaseModel):
    employee_code: str = Field(min_length=2, max_length=32)
    pin: str = Field(min_length=4, max_length=12)
    action: Literal["check_in", "check_out"]

class ThemeBody(BaseModel):
    theme: Literal["enterprise-dark", "clean-light", "modern-indigo", "security-command", "corporate-neutral"]

class BiometricEnrollBody(BaseModel):
    employee_code: str = Field(min_length=2, max_length=32)
    pin: str = Field(min_length=4, max_length=12)
    consent: Literal[True]
    images: list[str] = Field(min_length=3, max_length=3)

class FaceCheckBody(BaseModel):
    image: str = Field(min_length=100, max_length=1100000)
