"""Presence Attendance data model. UTC timestamps stored as naive UTC in MySQL DATETIME."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base


def utc_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Company(Base):
    __tablename__ = 'companies'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    timezone: Mapped[str] = mapped_column(String(64), default='Asia/Dubai')
    theme: Mapped[str] = mapped_column(String(40), default='enterprise-dark')
    accent_override: Mapped[str | None] = mapped_column(String(7), nullable=True)
    font_family: Mapped[str] = mapped_column(String(40), default='Inter')
    density: Mapped[str] = mapped_column(String(20), default='comfortable')
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)


class AdminUser(Base):
    __tablename__ = 'admin_users'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey('companies.id'), nullable=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), default='company_admin')
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    auth_version: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_notification_id: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)


class Subscription(Base):
    __tablename__ = 'subscriptions'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    plan: Mapped[str] = mapped_column(String(20))  # trial / monthly / annual
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    granted_by: Mapped[str] = mapped_column(String(100), default='registration')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)


class PaymentOrder(Base):
    __tablename__ = 'payment_orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    plan: Mapped[str] = mapped_column(String(20))
    amount_aed: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    reference: Mapped[str] = mapped_column(String(60), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Employee(Base):
    __tablename__ = 'employees'
    __table_args__ = (UniqueConstraint('company_id', 'employee_code', name='uq_employee_company_code'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    employee_code: Mapped[str] = mapped_column(String(32), index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(80))
    pin_hash: Mapped[str] = mapped_column(String(255))
    # Separate employee self-service password; kiosk PIN/face flows remain unchanged.
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_version: Mapped[int] = mapped_column(Integer, default=0)
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)


class Device(Base):
    __tablename__ = 'devices'
    __table_args__ = (UniqueConstraint('company_id', 'name', name='uq_device_company_name'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    pairing_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pairing_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)


class AttendanceEvent(Base):
    __tablename__ = 'attendance_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey('devices.id'))
    action: Mapped[str] = mapped_column(String(16))
    method: Mapped[str] = mapped_column(String(20), default='pin')
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive, index=True)


class SecurityEvent(Base):
    __tablename__ = 'security_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey('companies.id'), nullable=True, index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey('devices.id'), nullable=True)
    kind: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive, index=True)


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey('companies.id'), nullable=True, index=True)
    actor: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80))
    detail: Mapped[str] = mapped_column(String(255), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive, index=True)


class Notification(Base):
    __tablename__ = 'notifications'
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey('companies.id'), nullable=True, index=True)
    page: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(20), default='info')
    title: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)


class AppSetting(Base):
    __tablename__ = 'app_settings'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))


class FaceTemplate(Base):
    __tablename__ = 'face_templates'
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey('employees.id'), unique=True, index=True)
    encrypted_embedding: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(100))
    consent_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_naive)
