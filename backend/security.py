"""Password hashing and short-lived admin JWTs. NOT biometric verification."""
from __future__ import annotations
import hashlib
import os
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from .database import get_db
from .models import AdminUser, Device, Employee, Company

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=2)
DUMMY_HASH = hasher.hash("dummy-password-for-uniform-failure")

def hash_password(value: str) -> str:
    return hasher.hash(value)

def verify_password(value: str, stored_hash: str) -> bool:
    try:
        return bool(hasher.verify(stored_hash, value))
    except (VerificationError, ValueError):
        return False

def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be configured with at least 32 characters")
    return secret

def make_token(user: AdminUser) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user.id), "role": user.role, "av": user.auth_version, "iat": now, "exp": now + timedelta(hours=1)}, jwt_secret(), algorithm="HS256")

def require_admin(request: Request, db: Session = Depends(get_db)) -> AdminUser:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admin authentication required")
    try:
        payload = jwt.decode(authorization[7:], jwt_secret(), algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired admin session") from None
    user = db.get(AdminUser, user_id)
    if not user or payload.get("role") != user.role or user.role not in ("superadmin", "company_admin") or payload.get("av") != user.auth_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admin session no longer valid")
    return user

def require_device(request: Request, db: Session = Depends(get_db)) -> Device:
    device_id = request.headers.get("x-device-id", "")
    token = request.headers.get("x-device-token", "")
    try:
        parsed_id = int(device_id)
    except ValueError:
        raise HTTPException(401, "Kiosk is not paired") from None
    if not token or len(token) > 256:
        raise HTTPException(401, "Kiosk is not paired")
    device = db.get(Device, parsed_id)
    import hmac
    if not device or device.status != "paired" or not device.token_hash or not hmac.compare_digest(sha256(token), device.token_hash):
        raise HTTPException(401, "Invalid or revoked kiosk credential")
    return device


def make_employee_token(employee: Employee) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(employee.id), "role": "employee", "cid": employee.company_id,
                       "av": employee.auth_version, "iat": now, "exp": now + timedelta(hours=1)},
                      jwt_secret(), algorithm="HS256")


def require_employee(request: Request, db: Session = Depends(get_db)) -> Employee:
    authorization = request.headers.get("authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Employee sign-in required")
    try:
        payload = jwt.decode(authorization[7:], jwt_secret(), algorithms=["HS256"])
        if payload.get("role") != "employee":
            raise ValueError("Invalid role")
        employee_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Invalid or expired employee session") from None
    employee = db.get(Employee, employee_id)
    if (not employee or not employee.active or employee.company_id != payload.get("cid") or
            employee.auth_version != payload.get("av")):
        raise HTTPException(401, "Employee session no longer valid")
    company = db.get(Company, employee.company_id)
    if not company or not company.enabled:
        raise HTTPException(403, "Company account unavailable")
    return employee
