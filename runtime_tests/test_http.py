from platform_developer.app import create_app
from platform_developer.migrations import MIGRATIONS
import os
import time
from uuid import uuid4
import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from platform_backend_core import Database,MigrationRunner,TokenVerifier
from platform_backend_core.testing import temporary_database

def auth():
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public=key.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo)
    verifier=TokenVerifier(issuer='fixture',audience='fixture',public_key=public)
    def headers(scopes,workspace=None,actor=None):
        now=int(time.time())
        token=jwt.encode({'iss':'fixture','aud':'fixture','sub':str(actor or uuid4()),'ws':str(workspace or uuid4()),'iat':now,'exp':now+300,'jti':str(uuid4()),'scope':scopes},key,algorithm='RS256')
        return {'Authorization':'Bearer '+token,'Idempotency-Key':'fixture-key'}
    return verifier,headers

@pytest.fixture
def setup():
    dsn=os.environ.get('PLATFORM_TEST_DSN')
    if not dsn:pytest.skip('explicit PostgreSQL DSN required')
    with temporary_database(dsn,prefix='devh_') as temp:
        verifier,headers=auth()
        db=Database(temp.runtime_dsn)
        yield temp,db,verifier,headers
        db.close()

def test_missing_schema_is_not_ready(setup):
    temp,db,verifier,headers=setup
    with TestClient(create_app(db,verifier)) as c:
        assert c.get('/readyz').status_code==503
        assert c.get('/healthz').status_code==200

def test_authenticated_flag_api_conflict_and_bounds(setup):
    temp,db,verifier,headers=setup
    MigrationRunner(temp.admin_dsn,namespace='flags').apply(MIGRATIONS);temp.grant_schema('public')
    w=uuid4();h=headers('flags:read flags:write',w)
    with TestClient(create_app(db,verifier)) as c:
        assert c.get('/readyz').status_code==200
        assert c.get('/v1/flags').status_code==401
        assert c.get('/v1/flags',headers=headers('')).status_code==403
        body={'enabled':True,'rollout':10000}
        assert c.put('/v1/flags/pilot',headers=h,json=body).status_code==200
        assert c.put('/v1/flags/pilot',headers=h,json=body).status_code==409
        assert c.get('/v1/flags/pilot',headers=headers('flags:read')).status_code==404
        assert c.post('/v1/flags/pilot/evaluate',headers=h,json={'subject':'person'}).json()=={'enabled':True}
        assert c.put('/v1/flags/pilot',headers=h,json={'enabled':True,'rollout':True,'version':1}).status_code==422
        assert c.get('/v1/flags?limit=1000',headers=h).status_code==422


def test_applied_migration_checksum_required(setup):
    import psycopg
    from psycopg import sql
    temp,db,verifier,headers=setup
    MigrationRunner(temp.admin_dsn,namespace='flags').apply(MIGRATIONS);temp.grant_schema('public')
    with psycopg.connect(temp.admin_dsn) as admin:
        admin.execute("DELETE FROM platform_schema_migrations WHERE namespace=%s",('flags',))
    class Adapter:configured=True
    kwargs={'adapters':{'email':Adapter()}} if 'developer'=='communication' else {}
    with TestClient(create_app(db,verifier,**kwargs)) as c:
        assert c.get('/readyz').status_code==503


@pytest.mark.parametrize('kind,target,privilege',[('TABLE', 'feature_flags', 'SELECT'), ('TABLE', 'feature_flags', 'INSERT'), ('TABLE', 'feature_flags', 'UPDATE'), ('TABLE', 'feature_flags', 'DELETE'), ('SCHEMA', 'public', 'USAGE'), ('TABLE', 'platform_schema_migrations', 'SELECT')])
def test_readiness_requires_each_effective_privilege(setup,kind,target,privilege):
    import psycopg
    from psycopg import sql
    temp,db,verifier,headers=setup
    MigrationRunner(temp.admin_dsn,namespace='flags').apply(MIGRATIONS)
    temp.grant_schema('public')
    with psycopg.connect(temp.admin_dsn) as admin:
        admin.execute('REVOKE USAGE ON SCHEMA public FROM PUBLIC')
    class Adapter:configured=True
    kwargs={'adapters':{'email':Adapter()}} if 'developer'=='communication' else {}
    with TestClient(create_app(db,verifier,**kwargs)) as c:
        assert c.get('/readyz').status_code==200
        with psycopg.connect(temp.admin_dsn) as admin:
            admin.execute(sql.SQL('REVOKE {} ON {} {} FROM {}').format(sql.SQL(privilege),sql.SQL(kind),sql.Identifier(target),sql.Identifier(temp.runtime_role)))
        assert c.get('/readyz').status_code==503
        with psycopg.connect(temp.admin_dsn) as admin:
            admin.execute(sql.SQL('GRANT {} ON {} {} TO {}').format(sql.SQL(privilege),sql.SQL(kind),sql.Identifier(target),sql.Identifier(temp.runtime_role)))
        assert c.get('/readyz').status_code==200


def test_documented_cli_migrate_makes_http_ready(setup):
    import subprocess
    import sys
    from pathlib import Path
    import psycopg
    temp,db,verifier,headers=setup
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,'-m','platform_developer','migrate'],cwd=root,env={'DATABASE_URL':temp.admin_dsn,'PYTHONPATH':str(root/'src')},capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    temp.grant_schema('public')
    with TestClient(create_app(db,verifier)) as c:
        assert c.get('/readyz').status_code==200
    with psycopg.connect(temp.admin_dsn) as admin:
        assert admin.execute('SELECT namespace,version,checksum FROM platform_schema_migrations').fetchall()==[('flags',m.version,m.checksum) for m in MIGRATIONS]
