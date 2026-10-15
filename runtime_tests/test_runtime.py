from uuid import uuid4,UUID
from concurrent.futures import ThreadPoolExecutor
from platform_developer.store import FlagStore,Conflict
from platform_developer.migrations import MIGRATIONS
import os
import pytest
from platform_backend_core import Database, MigrationRunner
from platform_backend_core.testing import temporary_database

@pytest.fixture
def database():
    dsn=os.environ.get('PLATFORM_TEST_DSN')
    if not dsn: pytest.skip('explicit disposable PostgreSQL DSN required')
    with temporary_database(dsn,prefix='flag_') as temp:
        MigrationRunner(temp.admin_dsn,namespace='flags').apply(MIGRATIONS)
        temp.grant_schema('public')
        db=Database(temp.runtime_dsn)
        yield db,temp
        db.close()

def test_rollout_version_and_tenant_isolation(database):
    db,_=database;a,b=uuid4(),uuid4();s=FlagStore(db)
    row=s.put(a,'pilot',True,5000,['allowed'],None)
    assert row['version']==1
    assert s.get(b,'pilot') is None
    assert s.evaluate(a,'pilot','allowed') is True
    decisions=[s.evaluate(a,'pilot',str(i)) for i in range(100)]
    assert any(decisions) and not all(decisions)
    assert decisions==[FlagStore(db).evaluate(a,'pilot',str(i)) for i in range(100)]
    with pytest.raises(Conflict): s.put(a,'pilot',False,0,[],0)
    s.put(a,'pilot',False,10000,['allowed'],1)
    assert s.evaluate(a,'pilot','allowed') is False
    with pytest.raises(ValueError): s.put(a,'oops',True,10001,[],None)

def test_concurrent_update_has_one_winner(database):
    db,_=database;w=uuid4();s=FlagStore(db);s.put(w,'one',True,10000,[],None)
    def update(_):
        try: s.put(w,'one',False,0,[],1);return True
        except Conflict:return False
    with ThreadPoolExecutor(max_workers=4) as pool: assert sum(pool.map(update,range(4)))==1

def test_delete_version_and_force_rls(database):
    db,_=database;w=uuid4();s=FlagStore(db);s.put(w,'one',True,10000,[],None)
    with pytest.raises(Conflict):s.delete(w,'one',2)
    s.delete(w,'one',1);assert s.get(w,'one') is None
    with db.transaction(w) as c:
        with pytest.raises(Exception):c.execute('INSERT INTO feature_flags(workspace_id,name,enabled,rollout,subjects) VALUES (%s, %s, true, 1, %s)',(uuid4(),'foreign','[]'))
