"""Regression tests for portal-specific roles, scoped password resets and status."""
import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

# Same isolated test DB configuration as the v3 tests; never connects to XAMPP.
from tests.test_workflow import app
from backend.database import SessionLocal
from backend.models import AdminUser, Employee
from backend.security import make_employee_token


def headers(client, username, password):
    r = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert r.status_code == 200, r.text
    return {'Authorization': 'Bearer ' + r.json()['access_token']}


def register(client, slug, username):
    r=client.post('/api/public/register',json={
        'company_name': 'Test '+slug, 'slug': slug, 'email':slug+'@test.example',
        'username': username, 'password': 'old-admin-password-1234',
        'plan':'trial','timezone':'Asia/Dubai'
    })
    assert r.status_code==201, r.text
    return r.json()['company']['id']


def test_portal_passwords_isolation_and_status():
    with TestClient(app) as client:
        superuser=headers(client, 'platform-admin', 'platform-password-123456')
        a_id=register(client,'testing-v4-a','v4-owner-a')
        b_id=register(client,'testing-v4-b','v4-owner-b')
        a=headers(client,'v4-owner-a','old-admin-password-1234')
        b=headers(client,'v4-owner-b','old-admin-password-1234')
        assert client.get('/api/public/status').json()['database']=='operational'
        assert client.get('/api/super/system-status',headers=superuser).status_code==200
        assert client.get('/api/super/system-status',headers=a).status_code==403
        assert client.get('/api/portal/system-status',headers=a).status_code==200
        assert client.get('/api/portal/system-status',headers=superuser).status_code==403
        r=client.post('/api/portal/employees',headers=a,json={
            'employee_code':'V4-ONE','full_name':'Test Employee','department':'IT','pin':'2468'})
        assert r.status_code==201,r.text
        emp_id=r.json()['id']
        assert client.post(f'/api/portal/employees/{emp_id}/reset-password',headers=b,
                           json={'password':'employee-passphrase-123'}).status_code==404
        assert client.post(f'/api/portal/employees/{emp_id}/reset-password',headers=a,
                           json={'password':'employee-passphrase-123'}).status_code==200
        employee_auth=client.post('/api/employee/auth/login',json={
            'company_slug':'testing-v4-a','employee_code':'V4-ONE',
            'password':'employee-passphrase-123'})
        assert employee_auth.status_code==200,employee_auth.text
        employee_token={'Authorization':'Bearer '+employee_auth.json()['access_token']}
        assert client.get('/api/employee/calendar',headers=employee_token).status_code==200
        assert client.get('/api/portal/employees',headers=employee_token).status_code==401
        assert client.get('/api/super/companies',headers=employee_token).status_code==401
        assert client.post('/api/employee/auth/login',json={
            'company_slug':'testing-v4-b','employee_code':'V4-ONE',
            'password':'employee-passphrase-123'}).status_code==401
        assert client.get('/api/super/employees',headers=a).status_code==403
        listed=client.get('/api/super/employees',headers=superuser).json()
        assert any(x['id']==emp_id and x['company_id']==a_id for x in listed)
        admins=client.get(f'/api/super/companies/{a_id}/admins',headers=superuser).json()
        assert len(admins)==1
        admin_id=admins[0]['id']
        # Cannot target a different company admin through another company's ID.
        assert client.post(f'/api/super/companies/{b_id}/admins/{admin_id}/reset-password',headers=superuser,
                           json={'password':'new-admin-password-5678'}).status_code==404
        assert client.post(f'/api/super/companies/{a_id}/admins/{admin_id}/reset-password',headers=superuser,
                           json={'password':'new-admin-password-5678'}).status_code==200
        assert client.get('/api/portal/employees',headers=a).status_code==401
        a=headers(client,'v4-owner-a','new-admin-password-5678')
        assert client.post(f'/api/super/companies/{a_id}/employees/{emp_id}/reset-password',headers=superuser,
                           json={'password':'renewed-employee-password'}).status_code==200
        assert client.get('/api/employee/me',headers=employee_token).status_code==401
        assert client.post('/api/employee/auth/login',json={
            'company_slug':'testing-v4-a','employee_code':'V4-ONE',
            'password':'employee-passphrase-123'}).status_code==401
        new=client.post('/api/employee/auth/login',json={
            'company_slug':'testing-v4-a','employee_code':'V4-ONE',
            'password':'renewed-employee-password'})
        assert new.status_code==200,new.text
        new_token={'Authorization':'Bearer '+new.json()['access_token']}
        assert client.post('/api/employee/change-password',headers=new_token,json={
            'current_password':'renewed-employee-password','new_password':'third-employee-passphrase'}).status_code==200
        assert client.get('/api/employee/me',headers=new_token).status_code==401
