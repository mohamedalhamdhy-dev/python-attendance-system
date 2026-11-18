"""Presence Attendance — multi-tenant on-prem SaaS pilot API.

Money flows are DEMONSTRATIONS: checkout creates a pending order, not a payment.
OpenCV face matching is PILOT ONLY: no certified PAD/liveness or camera attestation.
No camera image is persisted. All tenant-scoped reads and writes enforce company_id.
"""
from __future__ import annotations
import csv
import io
import logging
import os
import re
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone, time as dt_time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pathlib import Path
from urllib.request import build_opener, ProxyHandler

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from .database import Base, engine, SessionLocal, get_db
from .models import (Company, Subscription, PaymentOrder, AdminUser, Employee, Device, AttendanceEvent,
                     SecurityEvent, AuditLog, Notification, FaceTemplate, utc_naive)
from .schemas import (LoginBody, PasswordChange, EmployeeCreate, EmployeePatch, PinReset,
                      DeviceCreate, PairBody, AttendanceBody, BiometricEnrollBody, FaceCheckBody)
from .security import (DUMMY_HASH, hash_password, verify_password, sha256, make_token,
                       require_admin, require_device, require_employee, make_employee_token, jwt_secret)
from .upgrade import migrate
from . import biometrics

LOG = logging.getLogger(__name__)
THEMES = ('enterprise-dark','clean-light','modern-indigo','security-command','corporate-neutral',
          'midnight-azure','forest-pro','sandstone','ocean-blue','rose-quartz','graphite','high-contrast')
PLANS = {'monthly': (100, 30), 'annual': (1000, 365)}
APP_TZ = os.getenv('APP_TIMEZONE','Asia/Dubai')
MIN_CHECKOUT_MINUTES = max(0, int(os.getenv('MIN_CHECKOUT_INTERVAL_MINUTES','30')))


def dt_iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def get_tz(company):
    try:
        return ZoneInfo(company.timezone if company else APP_TZ)
    except ZoneInfoNotFoundError:
        return ZoneInfo('UTC')


def to_local(value, company):
    return value.replace(tzinfo=timezone.utc).astimezone(get_tz(company))


def log(db, actor, action, detail='', company_id=None):
    db.add(AuditLog(company_id=company_id, actor=actor[:120], action=action[:80], detail=str(detail)[:255]))


def notify(db, company_id, page, title, message, severity='info'):
    db.add(Notification(company_id=company_id, page=page, title=title[:120],
                        message=message[:255], severity=severity))


def serialize_company(company, db):
    current = subscription_state(db, company)
    return {'id': company.id, 'name': company.name, 'slug': company.slug,
            'email': company.email, 'theme': company.theme, 'timezone': company.timezone,
            'accent_override':company.accent_override,'font_family':company.font_family,'density':company.density,
            'enabled': company.enabled, 'created_at': dt_iso(company.created_at), 'subscription':current}


def subscription_state(db, company):
    sub = db.scalar(select(Subscription).where(Subscription.company_id == company.id)
                    .order_by(Subscription.ends_at.desc(), Subscription.id.desc()).limit(1))
    if not company.enabled:
        status = 'suspended'
    elif not sub:
        status = 'pending'
    elif sub.ends_at <= utc_naive():
        status = 'expired'
    else:
        status = 'trial' if sub.plan == 'trial' else 'active'
    return {'status':status, 'plan':sub.plan if sub else None,
            'starts_at':dt_iso(sub.starts_at) if sub else None,
            'ends_at':dt_iso(sub.ends_at) if sub else None,
            'days_remaining': max(0, (sub.ends_at.date()-utc_naive().date()).days) if sub and status in ('trial','active') else 0}


def require_company(user: AdminUser = Depends(require_admin), db: Session = Depends(get_db)) -> Company:
    if user.role != 'company_admin' or not user.company_id:
        raise HTTPException(403, 'Company administrator access required')
    company = db.get(Company, user.company_id)
    if not company:
        raise HTTPException(403, 'Company unavailable')
    return company


def require_super(user: AdminUser = Depends(require_admin)) -> AdminUser:
    if user.role != 'superadmin' or user.company_id is not None:
        raise HTTPException(403, 'Platform administrator access required')
    return user


def require_active(company: Company = Depends(require_company), db: Session = Depends(get_db)) -> Company:
    state = subscription_state(db, company)
    if state['status'] not in ('active','trial'):
        raise HTTPException(402, 'Company subscription inactive. Open Billing to renew or contact the platform administrator.')
    return company


def active_device(db, dev):
    company = db.get(Company, dev.company_id)
    if not company or subscription_state(db, company)['status'] not in ('active','trial'):
        raise HTTPException(402, 'This company’s access has expired or been suspended. Contact your company administrator.')
    return company


def emp_json(emp, enrolled=False):
    return {'id':emp.id, 'employee_code':emp.employee_code, 'full_name':emp.full_name,
            'department':emp.department, 'active':emp.active,
            'created_at':dt_iso(emp.created_at), 'biometric_enrolled':enrolled,
            'portal_password_set': bool(emp.password_hash)}


def device_json(dev):
    online=bool(dev.last_seen and (utc_naive()-dev.last_seen).total_seconds()<150 and dev.status=='paired')
    return {'id':dev.id,'name':dev.name,'location':dev.location,'status':dev.status,
            'online':online,'last_seen':dt_iso(dev.last_seen),'created_at':dt_iso(dev.created_at)}


class RegisterCompany(BaseModel):
    company_name: str = Field(min_length=3, max_length=160)
    slug: str = Field(min_length=3, max_length=64, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    email: EmailStr
    username: str = Field(min_length=3, max_length=80, pattern=r'^[A-Za-z0-9_.-]+$')
    password: str = Field(min_length=12, max_length=128)
    plan: str = Field(pattern=r'^(trial|monthly|annual)$')
    timezone: str = Field(default='Asia/Dubai', max_length=64)
    model_config = ConfigDict(extra='forbid')

class PlanBody(BaseModel):
    plan: str = Field(pattern=r'^(monthly|annual)$')

class GrantBody(BaseModel):
    plan: str = Field(pattern=r'^(trial|monthly|annual)$')

class ThemeBody(BaseModel):
    theme: str | None = Field(default=None,min_length=3,max_length=40)
    accent_override: str | None = Field(default=None,pattern=r'^#[0-9A-Fa-f]{6}$')
    font_family: str | None = None
    density: str | None = None
    model_config = ConfigDict(extra='forbid')

class StatusBody(BaseModel):
    enabled: bool

class ReadBody(BaseModel):
    last_seen_id: int = Field(ge=0)

class AdminPasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)
    model_config = ConfigDict(extra='forbid')

class EmployeeLogin(BaseModel):
    company_slug: str = Field(min_length=3, max_length=64)
    employee_code: str = Field(min_length=2, max_length=32)
    password: str = Field(min_length=1, max_length=256)
    model_config = ConfigDict(extra='forbid')


def ensure_setup():
    jwt_secret()
    username = os.getenv('ADMIN_USERNAME','admin')
    password = os.getenv('ADMIN_PASSWORD','')
    if len(password)<12:
        raise RuntimeError('ADMIN_PASSWORD must have at least 12 characters. Run scripts/setup_env.py')
    migrate()
    with SessionLocal() as db:
        if not db.scalar(select(AdminUser.id).where(AdminUser.role=='superadmin').limit(1)):
            db.add(AdminUser(username=username,password_hash=hash_password(password),role='superadmin'))
            db.commit()


@asynccontextmanager
async def lifespan(_):
    ensure_setup()
    yield


app=FastAPI(title='Presence Attendance',version='4.0',docs_url=None,redoc_url=None,lifespan=lifespan)

@app.get('/health')
def health():
    return {'ok':True,'version':'4.0','face_matching_available':biometrics.available(),
            'liveness_verified':False,'payments_live':False}

def web_service_status():
    """Check only fixed internal service addresses, never user-provided URLs."""
    services = {'platform_portal': 'http://admin:80/',
                'company_portal': 'http://company:80/',
                'attendance_portal': 'http://client:80/'}
    status = {}
    opener = build_opener(ProxyHandler({}))
    for name, address in services.items():
        try:
            with opener.open(address, timeout=1.5) as response:
                status[name] = 'operational' if response.status == 200 else 'unavailable'
        except Exception:
            status[name] = 'unavailable'
    return status

@app.get('/api/public/status')
def public_status(db: Session = Depends(get_db)):
    # Deliberately excludes connection details, secrets, tenant counts, and internal hosts.
    db.execute(text('SELECT 1')).scalar_one()
    return {'api': 'operational', 'database': 'operational',
            'face_matching_available': biometrics.available(), 'live_payment_processing': False,
            'liveness_certified': False, 'web_portals': web_service_status(),
            'checked_at': dt_iso(utc_naive())}

@app.get('/api/public/plans')
def plans():
    return [{'code':'trial','amount_aed':0,'days':7},
            {'code':'monthly','amount_aed':100,'days':30},
            {'code':'annual','amount_aed':1000,'days':365}]

@app.post('/api/public/register',status_code=201)
def register(body:RegisterCompany,db:Session=Depends(get_db)):
    try: ZoneInfo(body.timezone)
    except ZoneInfoNotFoundError: raise HTTPException(422,'Invalid IANA timezone') from None
    company=Company(name=body.company_name.strip(),slug=body.slug,email=str(body.email).lower(),timezone=body.timezone)
    db.add(company)
    try:
        db.flush()
        user=AdminUser(company_id=company.id,username=body.username,password_hash=hash_password(body.password),role='company_admin')
        db.add(user)
        if body.plan=='trial':
            db.add(Subscription(company_id=company.id,plan='trial',starts_at=utc_naive(),
                                ends_at=utc_naive()+timedelta(days=7),granted_by='registration'))
        else:
            db.add(PaymentOrder(company_id=company.id,plan=body.plan,amount_aed=PLANS[body.plan][0],
                                reference='PA-'+secrets.token_hex(7).upper()))
        log(db,'registration','company.created',company.name,company.id)
        notify(db,None,'companies','New company registration',company.name)
        notify(db,company.id,'billing','Welcome to Presence Attendance',
               'Your workspace is ready. Select a plan to activate access.' if body.plan!='trial' else 'Your 7-day trial has started.')
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Company URL, email or username is already registered') from None
    return {'company':serialize_company(company,db),'message':'Account created. Sign in to continue.'}

@app.post('/api/auth/login')
def login(body:LoginBody,db:Session=Depends(get_db)):
    user=db.scalar(select(AdminUser).where(AdminUser.username==body.username))
    if not user:
        verify_password(body.password,DUMMY_HASH)
        raise HTTPException(401,'Invalid username or password')
    now=utc_naive()
    if user.locked_until and user.locked_until>now:
        raise HTTPException(429,'Account temporarily locked')
    if not verify_password(body.password,user.password_hash):
        user.failed_logins+=1
        if user.failed_logins>=5:
            user.failed_logins=0;user.locked_until=now+timedelta(minutes=15)
        db.commit();raise HTTPException(401,'Invalid username or password')
    user.failed_logins=0;user.locked_until=None
    log(db,user.username,'auth.login','',user.company_id)
    db.commit()
    return {'access_token':make_token(user),'username':user.username,'role':user.role,
            'company_id':user.company_id}

@app.get('/api/auth/me')
def me(user:AdminUser=Depends(require_admin),db:Session=Depends(get_db)):
    company=db.get(Company,user.company_id) if user.company_id else None
    return {'username':user.username,'role':user.role,'company_id':user.company_id,
            'company':serialize_company(company,db) if company else None}

@app.post('/api/auth/change-password')
def change_password(body:PasswordChange,db:Session=Depends(get_db),user:AdminUser=Depends(require_admin)):
    if not verify_password(body.current_password,user.password_hash):
        raise HTTPException(400,'Current password incorrect')
    if body.current_password==body.new_password:
        raise HTTPException(400,'Choose a new password')
    user.password_hash=hash_password(body.new_password);user.auth_version+=1
    log(db,user.username,'auth.password_changed','',user.company_id)
    db.commit()
    return {'message':'Password changed. Sign in again.'}

# Employee self-service does not use attendance PIN or biometric credentials.
@app.post('/api/employee/auth/login')
def employee_signin(body: EmployeeLogin, db: Session = Depends(get_db)):
    company = db.scalar(select(Company).where(Company.slug == body.company_slug.lower().strip()))
    employee = (db.scalar(select(Employee).where(Employee.company_id == company.id,
                          Employee.employee_code == body.employee_code.upper().strip())) if company else None)
    stored = employee.password_hash if employee and employee.password_hash and employee.active else DUMMY_HASH
    correct = verify_password(body.password, stored)
    now = utc_naive()
    if employee and employee.locked_until and employee.locked_until > now:
        raise HTTPException(429, 'Account temporarily locked')
    if not correct or not employee or not company or not company.enabled:
        if employee:
            employee.failed_logins += 1
            if employee.failed_logins >= 5:
                employee.failed_logins = 0
                employee.locked_until = now + timedelta(minutes=15)
            db.commit()
        raise HTTPException(401, 'Invalid company, employee ID, or password')
    employee.failed_logins = 0
    employee.locked_until = None
    log(db, 'employee:'+employee.employee_code, 'employee.login', '', company.id)
    db.commit()
    return {'access_token': make_employee_token(employee)}

@app.get('/api/employee/me')
def employee_me(emp: Employee = Depends(require_employee), db: Session = Depends(get_db)):
    company = db.get(Company, emp.company_id)
    return {'employee': emp_json(emp), 'company': {'name': company.name, 'slug': company.slug,
            'timezone': company.timezone, 'theme': company.theme}}

@app.get('/api/employee/calendar')
def own_calendar(month: str = Query(default_factory=lambda: utc_naive().strftime('%Y-%m')),
                 emp: Employee = Depends(require_employee), db: Session = Depends(get_db)):
    company = db.get(Company, emp.company_id)
    return employee_calendar(emp.id, month, db, company)

@app.post('/api/employee/change-password')
def employee_change_password(body: PasswordChange, emp: Employee = Depends(require_employee),
                             db: Session = Depends(get_db)):
    if not emp.password_hash or not verify_password(body.current_password, emp.password_hash):
        raise HTTPException(400, 'Current password incorrect')
    if body.current_password == body.new_password:
        raise HTTPException(400, 'Choose a different password')
    emp.password_hash = hash_password(body.new_password)
    emp.auth_version += 1
    log(db, 'employee:'+emp.employee_code, 'employee.password_changed', '', emp.company_id)
    db.commit()
    return {'message': 'Password changed; sign in again'}

# COMPANY PORTAL — every query is limited by the authenticated company's ID.
@app.get('/api/portal/summary')
def portal_summary(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    tz=get_tz(company);today=datetime.now(tz).date()
    b=datetime.combine(today,dt_time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    end=datetime.combine(today+timedelta(days=1),dt_time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    emps=db.scalars(select(Employee).where(Employee.company_id==company.id,Employee.active.is_(True))).all()
    events=db.scalars(select(AttendanceEvent).where(AttendanceEvent.company_id==company.id,
                          AttendanceEvent.recorded_at>=b,AttendanceEvent.recorded_at<end)
                      .order_by(AttendanceEvent.recorded_at,AttendanceEvent.id)).all()
    current={}
    for e in events:current[e.employee_id]=e.action
    present=sum(1 for x in emps if current.get(x.id)=='check_in')
    recent=attendance_rows(db,company.id,limit=8)
    trend=[]
    for offset in range(13,-1,-1):
        day=today-timedelta(days=offset)
        start=datetime.combine(day,dt_time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
        finish=datetime.combine(day+timedelta(days=1),dt_time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
        count=db.scalar(select(func.count(func.distinct(AttendanceEvent.employee_id))).where(
            AttendanceEvent.company_id==company.id,AttendanceEvent.action=='check_in',
            AttendanceEvent.recorded_at>=start,AttendanceEvent.recorded_at<finish)) or 0
        trend.append({'day':day.isoformat(),'count':count})
    return {'company':serialize_company(company,db),'total':len(emps),'present':present,
            'absent_or_offsite':len(emps)-present,'devices':db.scalar(select(func.count()).select_from(Device).where(Device.company_id==company.id)) or 0,
            'today_events':len(events),'trend':trend,'recent':recent,'timezone':company.timezone}

@app.get('/api/portal/employees')
def portal_employees(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    enrolled=set(db.scalars(select(FaceTemplate.employee_id).join(Employee)
                      .where(Employee.company_id==company.id)).all())
    return [emp_json(e,e.id in enrolled) for e in db.scalars(select(Employee)
            .where(Employee.company_id==company.id).order_by(Employee.id.desc())).all()]

@app.post('/api/portal/employees',status_code=201)
def add_employee(body:EmployeeCreate,db:Session=Depends(get_db),company:Company=Depends(require_active),user:AdminUser=Depends(require_admin)):
    emp=Employee(company_id=company.id,employee_code=body.employee_code.upper(),
                 full_name=body.full_name.strip(),department=body.department.strip(),pin_hash=hash_password(body.pin))
    db.add(emp)
    try:
        db.flush()
        log(db,user.username,'employee.created',emp.employee_code,company.id)
        notify(db,company.id,'employees','Employee registered',emp.full_name)
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Employee code already exists in this company') from None
    db.refresh(emp)
    return emp_json(emp)

@app.patch('/api/portal/employees/{employee_id}')
def patch_employee(employee_id:int,body:EmployeePatch,db:Session=Depends(get_db),company:Company=Depends(require_active),user:AdminUser=Depends(require_admin)):
    emp=db.scalar(select(Employee).where(Employee.id==employee_id,Employee.company_id==company.id))
    if not emp: raise HTTPException(404,'Employee not found')
    for k,v in body.model_dump(exclude_unset=True).items():
        if v is not None: setattr(emp,k,v.strip() if isinstance(v,str) else v)
    log(db,user.username,'employee.updated',emp.employee_code,company.id);db.commit()
    return emp_json(emp)

@app.post('/api/portal/employees/{employee_id}/reset-pin')
def reset_pin(employee_id:int,body:PinReset,db:Session=Depends(get_db),company:Company=Depends(require_active),user:AdminUser=Depends(require_admin)):
    emp=db.scalar(select(Employee).where(Employee.id==employee_id,Employee.company_id==company.id))
    if not emp: raise HTTPException(404,'Employee not found')
    emp.pin_hash=hash_password(body.pin);log(db,user.username,'employee.pin_reset',emp.employee_code,company.id)
    db.commit();return {'message':'PIN updated'}

@app.post('/api/portal/employees/{employee_id}/reset-password')
def portal_reset_employee_password(employee_id: int, body: AdminPasswordReset,
                                   db: Session = Depends(get_db),
                                   company: Company = Depends(require_company),
                                   user: AdminUser = Depends(require_admin)):
    employee = db.scalar(select(Employee).where(Employee.id == employee_id,
                           Employee.company_id == company.id))
    if not employee:
        raise HTTPException(404, 'Employee not found')
    employee.password_hash = hash_password(body.password)
    employee.auth_version += 1
    employee.failed_logins = 0
    employee.locked_until = None
    log(db, user.username, 'employee.password_reset', employee.employee_code, company.id)
    db.commit()
    return {'message': 'Employee portal password updated; previous sessions revoked'}

@app.delete('/api/portal/employees/{employee_id}/biometrics')
def delete_biometrics(employee_id:int,db:Session=Depends(get_db),company:Company=Depends(require_active),user:AdminUser=Depends(require_admin)):
    emp=db.scalar(select(Employee).where(Employee.id==employee_id,Employee.company_id==company.id))
    if not emp: raise HTTPException(404,'Employee not found')
    template=db.scalar(select(FaceTemplate).where(FaceTemplate.employee_id==employee_id))
    if not template: raise HTTPException(404,'Face template not found')
    db.delete(template);log(db,user.username,'biometric.deleted',emp.employee_code,company.id)
    db.commit();return {'message':'Face enrollment removed'}

@app.get('/api/portal/employees/{employee_id}/calendar')
def employee_calendar(employee_id:int,month:str=Query(default_factory=lambda:utc_naive().strftime('%Y-%m')),db:Session=Depends(get_db),company:Company=Depends(require_company)):
    emp=db.scalar(select(Employee).where(Employee.id==employee_id,Employee.company_id==company.id))
    if not emp: raise HTTPException(404,'Employee not found')
    if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):raise HTTPException(422,'Month must be YYYY-MM')
    year,mon=map(int,month.split('-'))
    if year<2000 or year>2100:raise HTTPException(422,'Invalid year')
    start=date(year,mon,1)
    next_month=date(year+1,1,1) if mon==12 else date(year,mon+1,1)
    tz=get_tz(company)
    utc_start=datetime.combine(start,dt_time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    utc_end=datetime.combine(next_month,dt_time.min,tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
    events=db.scalars(select(AttendanceEvent).where(AttendanceEvent.employee_id==emp.id,
        AttendanceEvent.company_id==company.id,AttendanceEvent.recorded_at>=utc_start,
        AttendanceEvent.recorded_at<utc_end).order_by(AttendanceEvent.recorded_at)).all()
    by_day={}
    for e in events:
        local=to_local(e.recorded_at,company)
        by_day.setdefault(local.date().isoformat(),[]).append({'action':e.action,'time':local.strftime('%H:%M'),
                                                                'timestamp':dt_iso(e.recorded_at),'method':e.method})
    today=datetime.now(tz).date()
    days=[];cursor=start
    while cursor<next_month:
        rows=by_day.get(cursor.isoformat(),[])
        ins=[v['time'] for v in rows if v['action']=='check_in']
        outs=[v['time'] for v in rows if v['action']=='check_out']
        if cursor>today:status='future'
        elif ins and outs:status='complete'
        elif ins:status='incomplete'
        elif cursor.weekday()>=5:status='weekend'
        else:status='no_record' # Leave/holidays aren't modeled: not an absence determination.
        days.append({'date':cursor.isoformat(),'weekday':cursor.weekday(),'status':status,
                     'check_in':ins[0] if ins else None,'check_out':outs[-1] if outs else None,'events':rows})
        cursor+=timedelta(days=1)
    return {'employee':emp_json(emp),'month':month,'timezone':company.timezone,'days':days}

@app.get('/api/portal/devices')
def portal_devices(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    return [device_json(d) for d in db.scalars(select(Device).where(Device.company_id==company.id)
        .order_by(Device.id.desc())).all()]

@app.post('/api/portal/devices',status_code=201)
def add_device(body:DeviceCreate,db:Session=Depends(get_db),company:Company=Depends(require_active),user:AdminUser=Depends(require_admin)):
    code=secrets.token_urlsafe(18)
    dev=Device(company_id=company.id,name=body.name.strip(),location=body.location.strip(),
        pairing_hash=sha256(code),pairing_expires=utc_naive()+timedelta(minutes=10))
    db.add(dev)
    try:
        db.flush();log(db,user.username,'device.created',dev.name,company.id)
        notify(db,company.id,'devices','Kiosk registered',dev.name)
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'A kiosk with this name already exists in this company') from None
    return {'device':device_json(dev),'pairing_code':code,'expires_minutes':10}

@app.post('/api/portal/devices/{device_id}/pair-code')
def new_code(device_id:int,db:Session=Depends(get_db),company:Company=Depends(require_active),user:AdminUser=Depends(require_admin)):
    dev=db.scalar(select(Device).where(Device.id==device_id,Device.company_id==company.id,Device.status!='revoked'))
    if not dev:raise HTTPException(404,'Kiosk unavailable')
    code=secrets.token_urlsafe(18)
    dev.pairing_hash=sha256(code);dev.pairing_expires=utc_naive()+timedelta(minutes=10)
    dev.token_hash=None;dev.status='pending';dev.last_seen=None
    log(db,user.username,'device.repair_requested',dev.name,company.id)
    db.commit();return {'pairing_code':code,'expires_minutes':10}

@app.post('/api/portal/devices/{device_id}/revoke')
def revoke_device(device_id:int,db:Session=Depends(get_db),company:Company=Depends(require_company),user:AdminUser=Depends(require_admin)):
    dev=db.scalar(select(Device).where(Device.id==device_id,Device.company_id==company.id))
    if not dev:raise HTTPException(404,'Kiosk not found')
    dev.status='revoked';dev.token_hash=None;dev.pairing_hash=None
    log(db,user.username,'device.revoked',dev.name,company.id)
    notify(db,company.id,'devices','Kiosk revoked',dev.name,'warning')
    db.commit();return {'message':'Kiosk revoked'}


def attendance_rows(db,company_id=None,limit=200):
    stmt=select(AttendanceEvent,Employee,Device).join(Employee,AttendanceEvent.employee_id==Employee.id).join(Device,AttendanceEvent.device_id==Device.id)
    if company_id is not None:stmt=stmt.where(AttendanceEvent.company_id==company_id)
    return [{'id':evt.id,'company_id':evt.company_id,'employee_id':emp.id,'employee_code':emp.employee_code,
             'full_name':emp.full_name,'department':emp.department,'device':dev.name,'location':dev.location,
             'action':evt.action,'method':evt.method,'recorded_at':dt_iso(evt.recorded_at)}
            for evt,emp,dev in db.execute(stmt.order_by(AttendanceEvent.id.desc()).limit(limit)).all()]

@app.get('/api/portal/attendance')
def portal_attendance(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    return attendance_rows(db,company.id)


def safe_csv(value):
    text=str(value if value is not None else '')
    return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text


def csv_export(rows,filename):
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['ID','Employee Code','Employee','Department','Action','Method','Kiosk','UTC Timestamp'])
    for r in rows:
        writer.writerow([safe_csv(r[k]) for k in ('id','employee_code','full_name','department','action','method','device','recorded_at')])
    return Response('\ufeff'+out.getvalue(),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':f'attachment; filename="{filename}"'})

@app.get('/api/portal/attendance/export')
def portal_export(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    return csv_export(attendance_rows(db,company.id,10000),f'presence-{company.slug}-{utc_naive().date()}.csv')

@app.get('/api/portal/security')
def portal_security(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    return [{'id':e.id,'kind':e.kind,'detail':e.detail,'created_at':dt_iso(e.created_at)} for e in db.scalars(
        select(SecurityEvent).where(SecurityEvent.company_id==company.id)
        .order_by(SecurityEvent.id.desc()).limit(200)).all()]

@app.get('/api/portal/audit')
def portal_audit(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    return [{'id':e.id,'actor':e.actor,'action':e.action,'detail':e.detail,'created_at':dt_iso(e.created_at)} for e in db.scalars(
        select(AuditLog).where(AuditLog.company_id==company.id).order_by(AuditLog.id.desc()).limit(200)).all()]

@app.get('/api/portal/biometric-status')
def portal_biometrics(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    count=db.scalar(select(func.count(FaceTemplate.id)).join(Employee).where(Employee.company_id==company.id)) or 0
    return {'available':biometrics.available(),'enrolled':count,'liveness_verified':False,'production_ready':False}

@app.get('/api/portal/theme')
def portal_theme(company:Company=Depends(require_company)):
    return {'theme':company.theme,'accent_override':company.accent_override,
            'font_family':company.font_family,'density':company.density,'available':list(THEMES)}

@app.put('/api/portal/theme')
def change_theme(body:ThemeBody,db:Session=Depends(get_db),company:Company=Depends(require_company),user:AdminUser=Depends(require_admin)):
    if body.theme is not None:
        if body.theme not in THEMES:raise HTTPException(422,'Unknown theme')
        company.theme=body.theme
    if 'accent_override' in body.model_fields_set:company.accent_override=body.accent_override
    if body.font_family is not None:
        if body.font_family not in ('Inter','Arial','Georgia','Verdana','Tahoma','system-ui'):
            raise HTTPException(422,'Unsupported font selection')
        company.font_family=body.font_family
    if body.density is not None:
        if body.density not in ('comfortable','compact'):
            raise HTTPException(422,'Unsupported density selection')
        company.density=body.density
    log(db,user.username,'theme.changed',company.theme,company.id)
    notify(db,company.id,'themes','Workspace appearance updated',company.theme)
    db.commit();return {'theme':company.theme,'accent_override':company.accent_override,
                        'font_family':company.font_family,'density':company.density}

@app.get('/api/portal/billing')
def portal_billing(db:Session=Depends(get_db),company:Company=Depends(require_company)):
    orders=db.scalars(select(PaymentOrder).where(PaymentOrder.company_id==company.id).order_by(PaymentOrder.id.desc()).limit(25)).all()
    return {'subscription':subscription_state(db,company),'orders':[order_json(o) for o in orders]}


def order_json(o):
    return {'id':o.id,'company_id':o.company_id,'plan':o.plan,'amount_aed':o.amount_aed,
            'status':o.status,'reference':o.reference,'created_at':dt_iso(o.created_at),'approved_at':dt_iso(o.approved_at)}

@app.post('/api/portal/orders',status_code=201)
def new_order(body:PlanBody,db:Session=Depends(get_db),company:Company=Depends(require_company)):
    if not company.enabled: raise HTTPException(403,'Company disabled')
    # Prevent accidental duplicate pending purchases; no real payment is processed.
    existing=db.scalar(select(PaymentOrder).where(PaymentOrder.company_id==company.id,
        PaymentOrder.plan==body.plan,PaymentOrder.status=='pending').limit(1))
    if existing:return order_json(existing)
    order=PaymentOrder(company_id=company.id,plan=body.plan,amount_aed=PLANS[body.plan][0],
                       reference='PA-'+secrets.token_hex(7).upper())
    db.add(order);db.flush()
    notify(db,None,'orders','New subscription order',f'{company.name}: AED {order.amount_aed}')
    notify(db,company.id,'billing','Order submitted',f'{order.reference} — pending manual review')
    log(db,f'company:{company.id}','order.created',order.reference,company.id)
    db.commit();return order_json(order)

# SUPERADMIN — global read/approve, never user-controlled company_id on company portal.
@app.get('/api/super/overview')
def super_overview(db:Session=Depends(get_db),_:AdminUser=Depends(require_super)):
    companies=db.scalars(select(Company).order_by(Company.id.desc())).all()
    statuses=[subscription_state(db,c)['status'] for c in companies]
    return {'companies':len(companies),'active':sum(x in ('trial','active') for x in statuses),
            'expired':sum(x in ('expired','pending','suspended') for x in statuses),
            'employees':db.scalar(select(func.count()).select_from(Employee)) or 0,
            'devices':db.scalar(select(func.count()).select_from(Device)) or 0,
            'events':db.scalar(select(func.count()).select_from(AttendanceEvent)) or 0,
            'pending_orders':db.scalar(select(func.count()).select_from(PaymentOrder).where(PaymentOrder.status=='pending')) or 0,
            'recent':attendance_rows(db,None,15),'companies_recent':[serialize_company(c,db) for c in companies[:8]]}

@app.get('/api/super/companies')
def super_companies(db:Session=Depends(get_db),_:AdminUser=Depends(require_super)):
    companies=db.scalars(select(Company).order_by(Company.id.desc())).all()
    return [{**serialize_company(c,db),
             'employees':db.scalar(select(func.count()).select_from(Employee).where(Employee.company_id==c.id)) or 0,
             'devices':db.scalar(select(func.count()).select_from(Device).where(Device.company_id==c.id)) or 0}
            for c in companies]

@app.get('/api/super/employees')
def super_employees(db: Session = Depends(get_db), _: AdminUser = Depends(require_super)):
    companies = {c.id: c.name for c in db.scalars(select(Company)).all()}
    return [{**emp_json(emp), 'company': companies.get(emp.company_id, 'Unknown'),
             'company_id': emp.company_id, 'portal_password_set': bool(emp.password_hash)}
            for emp in db.scalars(select(Employee).order_by(Employee.id.desc()).limit(2000)).all()]

@app.get('/api/super/companies/{company_id}/admins')
def super_company_admins(company_id: int, db: Session = Depends(get_db),
                         _: AdminUser = Depends(require_super)):
    if not db.get(Company, company_id):
        raise HTTPException(404, 'Company not found')
    users = db.scalars(select(AdminUser).where(AdminUser.company_id == company_id,
                  AdminUser.role == 'company_admin').order_by(AdminUser.id)).all()
    return [{'id': u.id, 'username': u.username} for u in users]

@app.post('/api/super/companies/{company_id}/admins/{admin_id}/reset-password')
def super_reset_company_admin(company_id: int, admin_id: int, body: AdminPasswordReset,
                              db: Session = Depends(get_db), user: AdminUser = Depends(require_super)):
    target = db.scalar(select(AdminUser).where(AdminUser.id == admin_id,
                      AdminUser.company_id == company_id, AdminUser.role == 'company_admin'))
    if not target:
        raise HTTPException(404, 'Company administrator not found')
    target.password_hash = hash_password(body.password)
    target.auth_version += 1
    target.failed_logins = 0
    target.locked_until = None
    log(db, user.username, 'company_admin.password_reset', target.username, company_id)
    notify(db, company_id, 'settings', 'Administrator credentials changed',
           'An administrator password was reset by platform support.', 'warning')
    db.commit()
    return {'message': 'Administrator password updated; previous sessions revoked'}

@app.post('/api/super/companies/{company_id}/employees/{employee_id}/reset-password')
def super_reset_employee_password(company_id: int, employee_id: int, body: AdminPasswordReset,
                                  db: Session = Depends(get_db), user: AdminUser = Depends(require_super)):
    employee = db.scalar(select(Employee).where(Employee.id == employee_id,
                         Employee.company_id == company_id))
    if not employee:
        raise HTTPException(404, 'Employee not found in this company')
    employee.password_hash = hash_password(body.password)
    employee.auth_version += 1
    employee.failed_logins = 0
    employee.locked_until = None
    log(db, user.username, 'employee.password_reset', employee.employee_code, company_id)
    notify(db, company_id, 'employees', 'Employee portal password reset', employee.employee_code)
    db.commit()
    return {'message': 'Employee password updated; previous sessions revoked'}

@app.post('/api/super/companies/{company_id}/status')
def change_company_status(company_id:int,body:StatusBody,db:Session=Depends(get_db),user:AdminUser=Depends(require_super)):
    c=db.get(Company,company_id)
    if not c:raise HTTPException(404,'Company not found')
    c.enabled=body.enabled
    log(db,user.username,'company.status_changed',f'{c.slug}: {c.enabled}')
    notify(db,c.id,'billing','Workspace status changed','Enabled' if c.enabled else 'Suspended','warning')
    db.commit();return serialize_company(c,db)


def grant(db,company,plan,actor):
    now=utc_naive()
    if plan=='trial':
        duration=7
        if db.scalar(select(Subscription.id).where(Subscription.company_id==company.id,Subscription.plan=='trial')):
            raise HTTPException(409,'Trial was already used. Select a paid subscription.')
    else:duration=PLANS[plan][1]
    current=db.scalar(select(Subscription).where(Subscription.company_id==company.id)
                     .order_by(Subscription.ends_at.desc()).limit(1))
    start=max(now,current.ends_at) if current else now
    sub=Subscription(company_id=company.id,plan=plan,starts_at=start,
                     ends_at=start+timedelta(days=duration),granted_by=actor)
    db.add(sub);db.flush()
    notify(db,company.id,'billing','Subscription activated',f'{plan.capitalize()} through {sub.ends_at.date()}')
    log(db,actor,'subscription.granted',f'{company.slug}: {plan} until {sub.ends_at.date()}')
    return sub

@app.post('/api/super/companies/{company_id}/grant')
def admin_grant(company_id:int,body:GrantBody,db:Session=Depends(get_db),user:AdminUser=Depends(require_super)):
    company=db.get(Company,company_id)
    if not company:raise HTTPException(404,'Company not found')
    sub=grant(db,company,body.plan,user.username);db.commit()
    return {'plan':sub.plan,'ends_at':dt_iso(sub.ends_at)}

@app.get('/api/super/orders')
def super_orders(db:Session=Depends(get_db),_:AdminUser=Depends(require_super)):
    orders=db.execute(select(PaymentOrder,Company).join(Company).order_by(PaymentOrder.id.desc()).limit(200)).all()
    return [{**order_json(order),'company':c.name} for order,c in orders]

@app.post('/api/super/orders/{order_id}/approve')
def approve_order(order_id:int,db:Session=Depends(get_db),user:AdminUser=Depends(require_super)):
    order=db.scalar(select(PaymentOrder).where(PaymentOrder.id==order_id).with_for_update())
    if not order: raise HTTPException(404,'Order not found')
    if order.status!='pending':raise HTTPException(409,'Order has already been processed')
    company=db.get(Company,order.company_id)
    if not company or not company.enabled:raise HTTPException(409,'Company is suspended or unavailable')
    sub=grant(db,company,order.plan,user.username)
    order.status='approved';order.approved_at=utc_naive()
    log(db,user.username,'order.approved',order.reference)
    db.commit();return {'reference':order.reference,'subscription_ends_at':dt_iso(sub.ends_at)}

@app.post('/api/super/orders/{order_id}/reject')
def reject_order(order_id:int,db:Session=Depends(get_db),user:AdminUser=Depends(require_super)):
    order=db.scalar(select(PaymentOrder).where(PaymentOrder.id==order_id).with_for_update())
    if not order:raise HTTPException(404,'Order not found')
    if order.status!='pending':raise HTTPException(409,'Order processed')
    order.status='rejected';notify(db,order.company_id,'billing','Order not approved',order.reference,'warning')
    log(db,user.username,'order.rejected',order.reference)
    db.commit();return {'status':'rejected'}

@app.get('/api/super/attendance')
def super_attendance(db:Session=Depends(get_db),_:AdminUser=Depends(require_super)):
    names={c.id:c.name for c in db.scalars(select(Company)).all()}
    return [{**r,'company':names.get(r['company_id'],'Unknown')} for r in attendance_rows(db,None,500)]

@app.get('/api/super/attendance/export')
def super_export(db:Session=Depends(get_db),_:AdminUser=Depends(require_super)):
    return csv_export(attendance_rows(db,None,10000),f'presence-platform-{utc_naive().date()}.csv')

@app.get('/api/super/security')
def super_security(db:Session=Depends(get_db),_:AdminUser=Depends(require_super)):
    return [{'id':e.id,'company_id':e.company_id,'kind':e.kind,'detail':e.detail,
             'created_at':dt_iso(e.created_at)} for e in db.scalars(
             select(SecurityEvent).order_by(SecurityEvent.id.desc()).limit(200)).all()]

@app.get('/api/super/audit')
def super_audit(db:Session=Depends(get_db),_:AdminUser=Depends(require_super)):
    return [{'id':e.id,'company_id':e.company_id,'actor':e.actor,'action':e.action,
             'detail':e.detail,'created_at':dt_iso(e.created_at)} for e in db.scalars(
             select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()]

# Poll-based live updates; no third-party broker, 3-5 second refresh in the browser.
@app.get('/api/notifications')
def notifications(after:int=Query(0,ge=0),db:Session=Depends(get_db),user:AdminUser=Depends(require_admin)):
    scope=(Notification.company_id==user.company_id) if user.role!='superadmin' else True
    base=select(Notification).where(scope)
    latest=db.scalar(select(func.max(Notification.id)).where(scope)) or 0
    new=db.scalars(base.where(Notification.id>after).order_by(Notification.id.asc()).limit(50)).all()
    unread=db.scalars(base.where(Notification.id>user.last_seen_notification_id).order_by(Notification.id.desc()).limit(1000)).all()
    counts={}
    for n in unread:counts[n.page]=counts.get(n.page,0)+1
    return {'latest_id':latest,'unread_count':len(unread),'counts':counts,
            'items':[{'id':n.id,'page':n.page,'title':n.title,'message':n.message,'severity':n.severity,
                      'created_at':dt_iso(n.created_at)} for n in new]}

@app.post('/api/notifications/read')
def notifications_read(body:ReadBody,db:Session=Depends(get_db),user:AdminUser=Depends(require_admin)):
    # Never let an unrelated company's event become a notification acknowledgement oracle.
    scope=(Notification.company_id==user.company_id) if user.role!='superadmin' else True
    latest=db.scalar(select(func.max(Notification.id)).where(scope)) or 0
    user.last_seen_notification_id=max(user.last_seen_notification_id,min(body.last_seen_id,latest))
    db.commit();return {'last_seen_id':user.last_seen_notification_id}

@app.get('/api/super/system-status')
def super_system_status(db: Session = Depends(get_db), _: AdminUser = Depends(require_super)):
    db.execute(text('SELECT 1')).scalar_one()
    count = db.scalar(select(func.count()).select_from(Device)) or 0
    live = db.scalar(select(func.count()).select_from(Device).where(
        Device.status == 'paired', Device.last_seen >= utc_naive() - timedelta(seconds=150))) or 0
    return {'api': 'operational', 'database': 'operational',
            'kiosks_registered': count, 'kiosks_online': live,
            'face_matching_available': biometrics.available(),
            'backup_schedule_configured': os.getenv('BACKUP_SCHEDULED', 'false').lower() == 'true',
            'web_portals': web_service_status(), 'checked_at': dt_iso(utc_naive())}

@app.get('/api/portal/system-status')
def company_system_status(db: Session = Depends(get_db),
                          company: Company = Depends(require_company)):
    db.execute(text('SELECT 1')).scalar_one()
    count = db.scalar(select(func.count()).select_from(Device).where(Device.company_id == company.id)) or 0
    live = db.scalar(select(func.count()).select_from(Device).where(
        Device.company_id == company.id, Device.status == 'paired',
        Device.last_seen >= utc_naive() - timedelta(seconds=150))) or 0
    return {'api': 'operational', 'database': 'operational',
            'kiosks_registered': count, 'kiosks_online': live,
            'face_matching_available': biometrics.available(),
            'web_portals': web_service_status(), 'checked_at': dt_iso(utc_naive())}

# KIOSK — belongs to exactly one company, checked independently on every request.
@app.post('/api/kiosk/pair')
def pair(body:PairBody,db:Session=Depends(get_db)):
    dev=db.scalar(select(Device).where(Device.pairing_hash==sha256(body.code),Device.status=='pending'))
    if not dev or not dev.pairing_expires or dev.pairing_expires<utc_naive():
        raise HTTPException(401,'Invalid or expired pairing code')
    active_device(db,dev)
    token=secrets.token_urlsafe(32)
    dev.token_hash=sha256(token);dev.pairing_hash=None;dev.pairing_expires=None;dev.status='paired'
    dev.last_seen=utc_naive()
    company=db.get(Company,dev.company_id)
    notify(db,company.id,'devices','Kiosk paired',dev.name)
    log(db,f'kiosk:{dev.id}','device.paired',dev.name,company.id)
    db.commit()
    return {'device_id':dev.id,'device_token':token,'name':dev.name,'location':dev.location,
            'company':company.name,'company_id':company.id}

@app.get('/api/kiosk/device')
def kiosk_device(dev:Device=Depends(require_device),db:Session=Depends(get_db)):
    company=db.get(Company,dev.company_id)
    return {**device_json(dev),'company':company.name,'timezone':company.timezone,'subscription':subscription_state(db,company)}

@app.post('/api/kiosk/heartbeat')
def heartbeat(dev:Device=Depends(require_device),db:Session=Depends(get_db)):
    dev.last_seen=utc_naive();db.commit();return {'ok':True}

@app.get('/api/kiosk/theme')
def kiosk_theme(dev:Device=Depends(require_device),db:Session=Depends(get_db)):
    c=db.get(Company,dev.company_id)
    return {'theme':c.theme,'accent_override':c.accent_override,'font_family':c.font_family,'density':c.density}

@app.post('/api/kiosk/unpair')
def unpair(dev:Device=Depends(require_device),db:Session=Depends(get_db)):
    dev.token_hash=None;dev.pairing_hash=None;dev.pairing_expires=None
    dev.status='pending';dev.last_seen=None
    log(db,f'kiosk:{dev.id}','device.unpaired',dev.name,dev.company_id)
    notify(db,dev.company_id,'devices','Kiosk unpaired',dev.name,'warning')
    db.commit();return {'message':'Kiosk disconnected. Use a new pairing code.'}


def record_for_employee(db,dev,emp,action,method):
    now=utc_naive()
    db.execute(select(Employee.id).where(Employee.id==emp.id).with_for_update()).first()
    previous=db.scalar(select(AttendanceEvent).where(AttendanceEvent.employee_id==emp.id,
        AttendanceEvent.company_id==dev.company_id).order_by(AttendanceEvent.recorded_at.desc(),
        AttendanceEvent.id.desc()).limit(1))
    if action=='auto':
        action='check_out' if previous and previous.action=='check_in' else 'check_in'
    if action=='check_in' and previous and previous.action=='check_in':
        db.commit();raise HTTPException(409,'Already checked in. Check out first.')
    if action=='check_out' and (not previous or previous.action!='check_in'):
        db.commit();raise HTTPException(409,'No active check-in')
    if action=='check_out' and previous and (now-previous.recorded_at).total_seconds()<MIN_CHECKOUT_MINUTES*60:
        db.commit();raise HTTPException(409,f'Check-out available after {MIN_CHECKOUT_MINUTES} minutes')
    evt=AttendanceEvent(company_id=dev.company_id,employee_id=emp.id,device_id=dev.id,action=action,
                        method=method,recorded_at=now)
    db.add(evt);dev.last_seen=now
    notify(db,dev.company_id,'attendance','Attendance '+('check-in' if action=='check_in' else 'check-out'),
           f'{emp.full_name} · {dev.name}')
    log(db,f'kiosk:{dev.id}','attendance.'+action,emp.employee_code+':'+method,dev.company_id)
    db.commit();db.refresh(evt)
    return {'event_id':evt.id,'employee_code':emp.employee_code,'full_name':emp.full_name,
            'department':emp.department,'action':action,'method':method,'recorded_at':dt_iso(evt.recorded_at),
            'biometric_matched':method=='face','liveness_verified':False,'biometric_verified':False}


def reject_kiosk(db,dev,kind):
    dev.failed_attempts+=1
    db.add(SecurityEvent(company_id=dev.company_id,device_id=dev.id,kind=kind,
                         detail='Kiosk credential or face check rejected'))
    if dev.failed_attempts>=8:
        dev.failed_attempts=0;dev.locked_until=utc_naive()+timedelta(minutes=5)
    notify(db,dev.company_id,'alerts','Kiosk verification rejected',kind,'warning')
    db.commit()

@app.post('/api/kiosk/attendance')
def kiosk_attendance(body:AttendanceBody,db:Session=Depends(get_db),dev:Device=Depends(require_device)):
    active_device(db,dev)
    now=utc_naive()
    if dev.locked_until and dev.locked_until>now:raise HTTPException(429,'Kiosk temporarily locked')
    emp=db.scalar(select(Employee).where(Employee.company_id==dev.company_id,
                 Employee.employee_code==body.employee_code.upper()))
    valid=verify_password(body.pin,emp.pin_hash if emp and emp.active else DUMMY_HASH)
    if not emp or not emp.active or not valid:
        reject_kiosk(db,dev,'invalid_pin');raise HTTPException(401,'Invalid employee code or PIN')
    dev.failed_attempts=0;dev.locked_until=None
    return record_for_employee(db,dev,emp,body.action,'pin')

@app.get('/api/kiosk/biometric-status')
def kiosk_biometrics(dev:Device=Depends(require_device),db:Session=Depends(get_db)):
    # Enrolled count belongs only to the device's registered company. Avoid identity disclosure.
    enrolled=db.scalar(select(func.count(FaceTemplate.id)).join(Employee, Employee.id==FaceTemplate.employee_id)
        .where(Employee.company_id==dev.company_id,Employee.active.is_(True))) or 0
    return {'available':biometrics.available(),'enrolled_count':int(enrolled),
            'liveness_verified':False,'production_ready':False}


def ensure_face_ready():
    if not biometrics.available():
        raise HTTPException(503,'Face enrollment is unavailable. An administrator must install and verify the face models and encryption key.')

@app.post('/api/kiosk/biometric/enroll',status_code=201)
def biometric_enroll(body:BiometricEnrollBody,db:Session=Depends(get_db),dev:Device=Depends(require_device)):
    active_device(db,dev);ensure_face_ready()
    if dev.locked_until and dev.locked_until>utc_naive():raise HTTPException(429,'Kiosk temporarily locked')
    emp=db.scalar(select(Employee).where(Employee.company_id==dev.company_id,
                  Employee.employee_code==body.employee_code.upper()))
    if not verify_password(body.pin,emp.pin_hash if emp and emp.active else DUMMY_HASH) or not emp or not emp.active:
        reject_kiosk(db,dev,'invalid_enrollment_pin');raise HTTPException(401,'Invalid employee details')
    db.execute(select(Employee.id).where(Employee.id==emp.id).with_for_update()).first()
    if db.scalar(select(FaceTemplate.id).where(FaceTemplate.employee_id==emp.id)):
        db.commit();raise HTTPException(409,'Already enrolled. Ask your company administrator to reset the face enrollment.')
    try:
        vector=biometrics.enroll(body.images)
        # Duplicate faces detected only within this company: never disclose identities across tenants.
        others=db.execute(select(FaceTemplate.employee_id,FaceTemplate.encrypted_embedding).join(Employee)
                 .where(Employee.company_id==dev.company_id)).all()
        for other_id,ciphertext in others:
            if biometrics.similarity(vector,biometrics.decrypt_vector(ciphertext,other_id))>=biometrics.MATCH_THRESHOLD:
                raise biometrics.FaceRejected('This face may already be enrolled in this company.')
        encrypted=biometrics.encrypt_vector(vector,emp.id)
    except biometrics.FaceRejected as exc:
        db.commit();raise HTTPException(422,str(exc)) from None
    except Exception:
        db.rollback();LOG.exception('Biometric enrollment error (no images logged)')
        raise HTTPException(503,'Face engine unavailable') from None
    db.add(FaceTemplate(employee_id=emp.id,encrypted_embedding=encrypted,model_version=biometrics.MODEL_VERSION))
    notify(db,dev.company_id,'employees','Face enrollment completed',emp.full_name)
    log(db,f'kiosk:{dev.id}','biometric.enrolled',emp.employee_code,dev.company_id)
    db.commit();return {'message':'Face enrolled','liveness_verified':False}

@app.post('/api/kiosk/biometric/identify')
def biometric_identify(body:FaceCheckBody,db:Session=Depends(get_db),dev:Device=Depends(require_device)):
    active_device(db,dev);ensure_face_ready()
    if dev.locked_until and dev.locked_until>utc_naive():raise HTTPException(429,'Kiosk temporarily locked')
    rows=db.execute(select(FaceTemplate.employee_id,FaceTemplate.encrypted_embedding).join(Employee)
       .where(Employee.company_id==dev.company_id,Employee.active.is_(True))).all()
    if not rows:raise HTTPException(409,'No enrolled faces for this company')
    try:identity=biometrics.identify(body.image,list(rows))
    except biometrics.FaceRejected as exc:
        reject_kiosk(db,dev,'face_capture_rejected');raise HTTPException(422,str(exc)) from None
    except Exception:
        db.rollback();LOG.exception('Face identify error (image data not logged)')
        raise HTTPException(503,'Face verification is unavailable') from None
    if identity is None:
        reject_kiosk(db,dev,'face_no_match');raise HTTPException(401,'Face not recognized')
    emp=db.scalar(select(Employee).where(Employee.id==identity,Employee.company_id==dev.company_id,
                 Employee.active.is_(True)))
    if not emp:raise HTTPException(401,'Face not recognized')
    dev.failed_attempts=0;dev.locked_until=None
    return record_for_employee(db,dev,emp,'auto','face')

# BACKUPS — platform-only, encrypted archive download; host scheduled runner performs exports.
@app.get('/api/super/backups')
def backups_list(_:AdminUser=Depends(require_super)):
    folder=Path(os.getenv('BACKUP_DIRECTORY','/app/backups')).resolve()
    files=sorted((p for p in folder.glob('presence-*.sql.gz.enc') if p.is_file()),reverse=True)[:100] if folder.is_dir() else []
    return {'directory':str(folder),'scheduled':os.getenv('BACKUP_SCHEDULED','false').lower()=='true',
            'cloud_enabled':bool(os.getenv('BACKUP_S3_BUCKET')),
            'files':[{'name':p.name,'bytes':p.stat().st_size,'modified_at':datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat()} for p in files]}

@app.get('/api/super/backups/{filename}')
def backup_download(filename:str,_:AdminUser=Depends(require_super)):
    if not re.fullmatch(r'presence-[0-9T-Z]+-[0-9a-f]{8}\.sql\.gz\.enc',filename):
        raise HTTPException(404,'Backup not found')
    path=Path(os.getenv('BACKUP_DIRECTORY','/app/backups')).resolve()/filename
    if not path.is_file():raise HTTPException(404,'Backup not found')
    # FastAPI protected endpoint; encrypted archives contain no readable SQL without separate key.
    return FileResponse(path,filename=filename,media_type='application/octet-stream')
