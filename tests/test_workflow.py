"""End-to-end API integration tests with isolated SQLite, never touch live XAMPP/MySQL."""
import base64
import os
import tempfile
from datetime import timedelta
from pathlib import Path

import numpy as np

DIR=tempfile.TemporaryDirectory(prefix='presence-saas-tests-')
os.environ['PRESENCE_TESTING']='1'
os.environ['DATABASE_URL']='sqlite:///'+str(Path(DIR.name)/'test.db')
os.environ['JWT_SECRET']='test-secret-unique-long-000000000000000000000000000000'
os.environ['ADMIN_USERNAME']='platform-admin'
os.environ['ADMIN_PASSWORD']='platform-password-123456'
os.environ['MIN_CHECKOUT_INTERVAL_MINUTES']='0'
os.environ.pop('BIOMETRIC_ENCRYPTION_KEY',None)

from fastapi.testclient import TestClient
from backend.main import app
from backend.database import SessionLocal
from backend.models import Company, Subscription
from backend import biometrics


def _login(client,username,password):
    res=client.post('/api/auth/login',json={'username':username,'password':password})
    assert res.status_code==200,res.text
    return {'Authorization':'Bearer '+res.json()['access_token']}


def _register(client,name,slug,username,plan='trial'):
    res=client.post('/api/public/register',json={'company_name':name,'slug':slug,
         'email':f'{slug}@example.org','username':username,'password':'company-safe-password-567',
         'plan':plan,'timezone':'Asia/Dubai'})
    assert res.status_code==201,res.text
    return res.json()['company']


def test_saas_lifecycle_and_tenant_isolation(monkeypatch):
    with TestClient(app) as client:
        assert client.get('/health').json()['payments_live'] is False
        superhead=_login(client,'platform-admin','platform-password-123456')
        a=_register(client,'Kings Palace Real Estate','kings-palace','kings_owner')
        b=_register(client,'Second Company','second-company','second_owner')
        assert client.post('/api/public/register',json={'company_name':'Same','slug':'kings-palace',
             'email':'x@example.com','username':'another','password':'123456789012','plan':'trial'}).status_code==409
        ha=_login(client,'kings_owner','company-safe-password-567')
        hb=_login(client,'second_owner','company-safe-password-567')
        assert client.get('/api/super/companies',headers=ha).status_code==403
        assert client.get('/api/portal/employees',headers=superhead).status_code==403
        assert client.get('/api/portal/billing',headers=ha).json()['subscription']['status']=='trial'

        emp_body={'employee_code':'EMP-001','full_name':'A Employee','department':'IT Department','pin':'2486'}
        emp_a=client.post('/api/portal/employees',json=emp_body,headers=ha)
        assert emp_a.status_code==201,emp_a.text
        emp_b=client.post('/api/portal/employees',json={**emp_body,'full_name':'B Employee'},headers=hb)
        assert emp_b.status_code==201,emp_b.text
        emp_a_id=emp_a.json()['id'];emp_b_id=emp_b.json()['id']
        assert emp_a_id!=emp_b_id
        assert client.patch(f'/api/portal/employees/{emp_b_id}',headers=ha,json={'full_name':'Hacked'}).status_code==404
        assert client.get(f'/api/portal/employees/{emp_b_id}/calendar',headers=ha).status_code==404
        assert client.post(f'/api/portal/employees/{emp_b_id}/reset-pin',headers=ha,json={'pin':'9999'}).status_code==404
        dev_a=client.post('/api/portal/devices',headers=ha,json={'name':'Reception','location':'Building A'}).json()
        dev_b=client.post('/api/portal/devices',headers=hb,json={'name':'Reception','location':'Building B'}).json()
        assert client.post(f"/api/portal/devices/{dev_b['device']['id']}/revoke",headers=ha).status_code==404
        paired=client.post('/api/kiosk/pair',json={'code':dev_a['pairing_code']})
        assert paired.status_code==200,paired.text
        kiosk={'X-Device-Id':str(paired.json()['device_id']),'X-Device-Token':paired.json()['device_token']}
        assert paired.json()['company_id']==a['id']
        initial_bio=client.get('/api/kiosk/biometric-status',headers=kiosk).json()
        assert initial_bio['enrolled_count']==0 and initial_bio['production_ready'] is False
        assert client.post('/api/kiosk/pair',json={'code':dev_a['pairing_code']}).status_code==401
        wrong=client.post('/api/kiosk/attendance',headers=kiosk,
             json={'employee_code':'EMP-001','pin':'9999','action':'check_in'})
        assert wrong.status_code==401
        checkin=client.post('/api/kiosk/attendance',headers=kiosk,
             json={'employee_code':'EMP-001','pin':'2486','action':'check_in'})
        assert checkin.status_code==200,checkin.text
        assert checkin.json()['full_name']=='A Employee'
        assert checkin.json()['biometric_verified'] is False
        assert client.post('/api/kiosk/attendance',headers=kiosk,
             json={'employee_code':'EMP-001','pin':'2486','action':'check_in'}).status_code==409
        cal=client.get(f'/api/portal/employees/{emp_a_id}/calendar',headers=ha)
        assert cal.status_code==200 and any(d['check_in'] for d in cal.json()['days'])
        assert len(client.get('/api/portal/attendance',headers=hb).json())==0
        assert len(client.get('/api/portal/attendance',headers=ha).json())==1
        assert len(client.get('/api/super/attendance',headers=superhead).json())==1
        assert 'A Employee' in client.get('/api/portal/attendance/export',headers=ha).text
        assert 'A Employee' not in client.get('/api/portal/attendance/export',headers=hb).text
        # Notifications never cross tenant; platform sees all.
        n_a=client.get('/api/notifications?after=0',headers=ha).json()
        n_b=client.get('/api/notifications?after=0',headers=hb).json()
        assert any('A Employee' in n['message'] for n in n_a['items'])
        assert all('A Employee' not in n['message'] for n in n_b['items'])
        assert client.post('/api/notifications/read',headers=ha,json={'last_seen_id':n_a['latest_id']}).status_code==200
        assert client.get('/api/notifications',headers=ha).json()['unread_count']==0

        assert client.put('/api/portal/theme',headers=ha,json={'theme':'forest-pro'}).status_code==200
        assert client.get('/api/kiosk/theme',headers=kiosk).json()['theme']=='forest-pro'
        assert client.get('/api/portal/theme',headers=hb).json()['theme']=='enterprise-dark'

        # Use controlled embeddings to test AES-GCM lifecycle without claiming real camera or PAD accuracy.
        monkeypatch.setenv('BIOMETRIC_ENCRYPTION_KEY',base64.urlsafe_b64encode(b'B'*32).decode())
        monkeypatch.setattr(biometrics,'available',lambda:True)
        vector=np.zeros(128,dtype=np.float32);vector[0]=1
        monkeypatch.setattr(biometrics,'enroll',lambda _images:vector)
        monkeypatch.setattr(biometrics,'extract',lambda _image:vector)
        enrollment={'employee_code':'EMP-001','pin':'2486','consent':True,'images':['x'*120]*3}
        assert client.post('/api/kiosk/biometric/enroll',headers=kiosk,json={**enrollment,'consent':False}).status_code==422
        assert client.post('/api/kiosk/biometric/enroll',headers=kiosk,json=enrollment).status_code==201
        assert client.get('/api/kiosk/biometric-status',headers=kiosk).json()['enrolled_count']==1
        duplicate=client.post('/api/kiosk/biometric/enroll',headers=kiosk,json=enrollment)
        assert duplicate.status_code==409 and 'Already enrolled' in duplicate.json()['detail']
        assert client.get('/api/portal/employees',headers=ha).json()[0]['biometric_enrolled'] is True
        face=client.post('/api/kiosk/biometric/identify',headers=kiosk,json={'image':'x'*120})
        assert face.status_code==200,face.text
        assert face.json()['action']=='check_out' and face.json()['method']=='face'
        assert face.json()['liveness_verified'] is False
        assert face.json()['biometric_verified'] is False
        assert client.delete(f'/api/portal/employees/{emp_b_id}/biometrics',headers=ha).status_code==404
        assert client.delete(f'/api/portal/employees/{emp_a_id}/biometrics',headers=ha).status_code==200
        assert client.get('/api/kiosk/biometric-status',headers=kiosk).json()['enrolled_count']==0

        # Expire company A: updates and kiosk attendance must fail closed, billing remains accessible.
        with SessionLocal() as db:
            sub=db.query(Subscription).filter(Subscription.company_id==a['id']).first()
            from backend.models import utc_naive
            sub.ends_at=utc_naive()-timedelta(seconds=1)
            db.commit()
        assert client.post('/api/kiosk/attendance',headers=kiosk,
            json={'employee_code':'EMP-001','pin':'2486','action':'check_in'}).status_code==402
        assert client.post('/api/portal/employees',json={**emp_body,'employee_code':'EMP-002'},headers=ha).status_code==402
        assert client.get('/api/portal/billing',headers=ha).json()['subscription']['status']=='expired'
        order=client.post('/api/portal/orders',headers=ha,json={'plan':'monthly'})
        assert order.status_code==201,order.text
        assert order.json()['amount_aed']==100 and order.json()['status']=='pending'
        oid=order.json()['id']
        assert client.post(f'/api/super/orders/{oid}/approve',headers=ha).status_code==403
        assert client.get('/api/super/orders',headers=superhead).json()[0]['company']=='Kings Palace Real Estate'
        approved=client.post(f'/api/super/orders/{oid}/approve',headers=superhead)
        assert approved.status_code==200,approved.text
        assert client.post(f'/api/super/orders/{oid}/approve',headers=superhead).status_code==409
        assert client.get('/api/portal/billing',headers=ha).json()['subscription']['status']=='active'
        assert client.post('/api/kiosk/unpair',headers=kiosk).status_code==200
        assert client.get('/api/kiosk/device',headers=kiosk).status_code==401
        assert client.post('/api/portal/devices',headers=ha,json={'name':'Reception','location':'duplicate'}).status_code==409
        assert client.get('/api/super/overview',headers=superhead).json()['companies']>=2


def test_subscriptions_and_suspension():
    with TestClient(app) as client:
        superhead=_login(client,'platform-admin','platform-password-123456')
        company=_register(client,'Pending Company','pending-company','pending_owner','annual')
        companyhead=_login(client,'pending_owner','company-safe-password-567')
        assert company['subscription']['status']=='pending'
        assert client.post('/api/portal/devices',headers=companyhead,
               json={'name':'Front Desk','location':'HQ'}).status_code==402
        pending=client.get('/api/super/orders',headers=superhead).json()
        order=next(o for o in pending if o['company_id']==company['id'])
        assert order['amount_aed']==1000
        assert client.post(f"/api/super/orders/{order['id']}/approve",headers=superhead).status_code==200
        assert client.get('/api/portal/billing',headers=companyhead).json()['subscription']['plan']=='annual'
        suspended=client.post(f"/api/super/companies/{company['id']}/status",headers=superhead,json={'enabled':False})
        assert suspended.status_code==200
        assert client.post('/api/portal/employees',headers=companyhead,json={
            'employee_code':'S1','full_name':'Test User','department':'HR','pin':'1234'}).status_code==402
