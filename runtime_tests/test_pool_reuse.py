"""Real single-connection pool regression after successful and conflicting traffic."""
import os
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from fastapi.testclient import TestClient
from platform_backend_core import Database, MigrationRunner
from platform_backend_core.testing import temporary_database
from test_http import auth

from platform_developer.app import create_app
from platform_developer.migrations import MIGRATIONS
from platform_developer.store import FlagStore, Conflict


@pytest.fixture
def pooled():
    with temporary_database(os.environ['PLATFORM_TEST_DSN'],prefix='reuse_deve_') as temp:
        MigrationRunner(temp.admin_dsn,namespace='flags').apply(MIGRATIONS)
        temp.grant_schema()
        database=Database(temp.runtime_dsn,min_size=1,max_size=1)
        verifier,headers=auth()
        try:
            yield database,verifier,headers
        finally:
            database.close()


def assert_repeated_ready(database,store):
    for _ in range(3):
        assert database.ready() is True
        assert store.ready() is True


def test_store_pool_reuse_after_flag_conflict_and_isolation(pooled):
    database,_,_=pooled
    store=FlagStore(database);workspace,foreign=uuid4(),uuid4()
    assert_repeated_ready(database,store)
    row=store.put(workspace,'fixture',True,10000,[],None)
    assert store.get(workspace,'fixture')['version']==row['version']
    assert len(store.list(workspace))==1 and store.list(foreign)==[]
    assert store.get(foreign,'fixture') is None
    assert store.evaluate(workspace,'fixture','fixture-subject') is True
    with pytest.raises(Conflict):store.put(workspace,'fixture',False,0,[],None)
    with pytest.raises(Conflict):store.delete(workspace,'fixture',2)
    store.delete(workspace,'fixture',1)
    assert store.get(workspace,'fixture') is None
    assert_repeated_ready(database,store)


def test_http_pool_reuse_after_success_and_conflict(pooled):
    database,verifier,headers=pooled
    own=headers('flags:read flags:write',uuid4());foreign=headers('flags:read',uuid4())
    with TestClient(create_app(database,verifier)) as client:
        assert client.get('/readyz').status_code==200
        body={'enabled':True,'rollout':10000}
        assert client.put('/v1/flags/fixture',headers=own,json=body).status_code==200
        assert len(client.get('/v1/flags',headers=own).json())==1
        assert client.get('/v1/flags',headers=foreign).json()==[]
        assert client.get('/v1/flags/fixture',headers=foreign).status_code==404
        assert client.put('/v1/flags/fixture',headers=own,json=body).status_code==409
        assert client.put('/v1/flags/fixture',headers=own,json=body|{'rollout':True}).status_code==422
        for _ in range(3):
            assert client.get('/readyz').status_code==200
            assert database.ready() is True
