import datetime
import os
import pytest
from sqlalchemy import text

import models
import v12_service

BASIC={"ingredients":[{"name":"หมูสับ","quantity":100,"unit":"กรัม"}]}


def test_new_user_gets_free_plan_and_usage(client):
    r=client.post('/register',json={'username':'freeuser','password':'secret123'})
    assert r.status_code==201
    token=client.post('/login',json={'username':'freeuser','password':'secret123'}).json()['access_token']
    h={'Authorization':'Bearer '+token}
    u=client.get('/usage',headers=h).json()
    assert u['plan_name']=='Free' and u['used']==0 and u['limit']==2 and u['remaining']==2


def test_usage_charged_only_after_success(client, monkeypatch):
    r=client.post('/register',json={'username':'usageuser','password':'secret123'}); assert r.status_code==201
    token=client.post('/login',json={'username':'usageuser','password':'secret123'}).json()['access_token']; h={'Authorization':'Bearer '+token}
    import ai_service
    monkeypatch.setattr(ai_service, 'analyze', lambda payload: {"recommendations":[],"disclaimer":"x","source":"mock"})
    assert client.post('/analyze-food',json=BASIC,headers=h).status_code==200
    assert client.get('/usage',headers=h).json()['used']==1
    def fail(payload): raise ai_service.AIError('AI down',502)
    monkeypatch.setattr(ai_service, 'analyze', fail)
    assert client.post('/analyze-food',json=BASIC,headers=h).status_code==502
    assert client.get('/usage',headers=h).json()['used']==1


def test_free_limit_blocks_third_success(client, monkeypatch):
    r=client.post('/register',json={'username':'limituser','password':'secret123'}); assert r.status_code==201
    token=client.post('/login',json={'username':'limituser','password':'secret123'}).json()['access_token']; h={'Authorization':'Bearer '+token}
    import ai_service
    monkeypatch.setattr(ai_service, 'analyze', lambda payload: {"recommendations":[],"disclaimer":"x","source":"mock"})
    assert client.post('/analyze-food',json=BASIC,headers=h).status_code==200
    assert client.post('/analyze-food',json=BASIC,headers=h).status_code==200
    r=client.post('/analyze-food',json=BASIC,headers=h)
    assert r.status_code==429


def test_payment_success_activates_paid_and_failed_does_not(client):
    r=client.post('/register',json={'username':'payuser','password':'secret123'}); assert r.status_code==201
    token=client.post('/login',json={'username':'payuser','password':'secret123'}).json()['access_token']; h={'Authorization':'Bearer '+token}
    plans=client.get('/subscription/plans').json(); paid=next(p for p in plans if p['price']>0)
    p=client.post('/payment/create',json={'plan_id':paid['id']},headers=h); assert p.status_code==200
    pid=p.json()['id']
    f=client.post(f'/payment/webhook?payment_id={pid}&success=false',headers=h); assert f.status_code==200 and f.json()['status']=='failed'
    assert client.get('/subscription',headers=h).json()['plan']['name']=='Free'
    p2=client.post('/payment/create',json={'plan_id':paid['id']},headers=h); pid2=p2.json()['id']
    s=client.post(f'/payment/webhook?payment_id={pid2}&success=true',headers=h); assert s.status_code==200 and s.json()['status']=='success'
    sub=client.get('/subscription',headers=h).json(); assert sub['plan']['name']=='Pro'
    assert client.get('/usage',headers=h).json()['limit']==paid['usage_limit']


def test_admin_api_requires_role(client):
    r=client.post('/register',json={'username':'normaladmincheck','password':'secret123'}); assert r.status_code==201
    token=client.post('/login',json={'username':'normaladmincheck','password':'secret123'}).json()['access_token']
    r=client.get('/admin/dashboard',headers={'Authorization':'Bearer '+token})
    assert r.status_code==403


def test_admin_api_with_admin_role(client):
    r=client.post('/register',json={'username':'admincheck','password':'secret123'}); assert r.status_code==201
    from database import SessionLocal
    db=SessionLocal(); u=db.query(models.User).filter_by(username='admincheck').first(); u.role='admin'; db.commit(); db.close()
    token=client.post('/login',json={'username':'admincheck','password':'secret123'}).json()['access_token']
    r=client.get('/admin/dashboard',headers={'Authorization':'Bearer '+token})
    assert r.status_code==200
    assert 'estimated_ai_cost' in r.json()


def test_register_cannot_self_assign_admin(client, monkeypatch):
    monkeypatch.setenv('ADMIN_USERNAME', 'wannabeadmin')
    assert client.post('/register', json={'username': 'wannabeadmin', 'password': 'secret123'}).status_code == 201
    t = client.post('/login', json={'username': 'wannabeadmin', 'password': 'secret123'}).json()['access_token']
    assert client.get('/admin/dashboard', headers={'Authorization': 'Bearer ' + t}).status_code == 403


def test_users_endpoints_are_protected(client, auth_headers):
    assert client.get('/users', headers=auth_headers).status_code == 403
    me = client.get('/me', headers=auth_headers).json()
    assert client.get(f"/users/{me['id']}", headers=auth_headers).status_code == 200
    assert client.get(f"/users/{me['id'] + 9999}", headers=auth_headers).status_code == 403
