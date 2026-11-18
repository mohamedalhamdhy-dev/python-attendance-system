"""Idempotent forward-only bridge from v1/v2 MySQL schema to the SaaS schema.

For production, take a database backup first, review the DDL and migrate to Alembic.
No rows are removed here; existing records join a dedicated Legacy Workspace.
"""
from sqlalchemy import inspect, text
from .database import Base, engine, SessionLocal
from .models import Company, AdminUser, Employee, Device, AttendanceEvent, SecurityEvent, AuditLog, Subscription, utc_naive

ADDITIONS = {
    'companies': {'accent_override':'VARCHAR(7) NULL', 'font_family':"VARCHAR(40) NOT NULL DEFAULT 'Inter'", 'density':"VARCHAR(20) NOT NULL DEFAULT 'comfortable'"},
    'admin_users': {'company_id':'INTEGER NULL', 'last_seen_notification_id':'INTEGER NOT NULL DEFAULT 0'},
    'employees': {'company_id':'INTEGER NULL', 'password_hash':'VARCHAR(255) NULL', 'auth_version':'INTEGER NOT NULL DEFAULT 0', 'failed_logins':'INTEGER NOT NULL DEFAULT 0', 'locked_until':'DATETIME NULL'},
    'devices': {'company_id':'INTEGER NULL'},
    'attendance_events': {'company_id':'INTEGER NULL'},
    'security_events': {'company_id':'INTEGER NULL'},
    'audit_logs': {'company_id':'INTEGER NULL'},
}


def migrate():
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        for table, columns in ADDITIONS.items():
            current = {col['name'] for col in inspect(conn).get_columns(table)}
            for name, definition in columns.items():
                if name not in current:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))
        if engine.dialect.name == 'mysql':
            # Older releases have globally UNIQUE employee_code/device name; scope by tenant.
            for table, column, replacement in [('employees','employee_code','uq_employee_company_code'),
                                               ('devices','name','uq_device_company_name')]:
                unique_indexes = inspect(conn).get_unique_constraints(table)
                for info in unique_indexes:
                    if info['column_names'] == [column]:
                        idx = info['name']
                        if idx and idx != 'PRIMARY':
                            conn.execute(text(f'ALTER TABLE `{table}` DROP INDEX `{idx}`'))
                if not any(c['name'] == replacement for c in inspect(conn).get_unique_constraints(table)):
                    conn.execute(text(f'ALTER TABLE `{table}` ADD UNIQUE KEY `{replacement}` (`company_id`, `{column}`)'))
    with SessionLocal() as db:
        # Existing employees/devices belong to one explicit legacy tenant, not to new registrants.
        if db.query(Employee).filter(Employee.company_id.is_(None)).first() or db.query(Device).filter(Device.company_id.is_(None)).first():
            legacy = db.query(Company).filter(Company.slug == 'legacy-workspace').first()
            if not legacy:
                legacy = Company(name='Legacy Workspace', slug='legacy-workspace', email='legacy@localhost.invalid')
                db.add(legacy)
                db.flush()
            for cls in (Employee, Device):
                db.query(cls).filter(cls.company_id.is_(None)).update({cls.company_id:legacy.id}, synchronize_session=False)
            for evt in db.query(AttendanceEvent).filter(AttendanceEvent.company_id.is_(None)).all():
                emp = db.get(Employee, evt.employee_id)
                evt.company_id = emp.company_id if emp else legacy.id
            for evt in db.query(SecurityEvent).filter(SecurityEvent.company_id.is_(None), SecurityEvent.device_id.is_not(None)).all():
                dev = db.get(Device, evt.device_id)
                if dev: evt.company_id = dev.company_id
            if not db.query(Subscription).filter(Subscription.company_id == legacy.id).first():
                from datetime import timedelta
                db.add(Subscription(company_id=legacy.id, plan='annual', starts_at=utc_naive(),
                                    ends_at=utc_naive()+timedelta(days=365), granted_by='migration'))
        db.commit()
