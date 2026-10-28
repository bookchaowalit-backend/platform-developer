"""Only domain validation maps to 422; any other ValueError is a server bug (redacted 500).

Offline: the store is replaced or fails before touching the database.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from test_http import auth

from platform_developer import store as store_module
from platform_developer.app import create_app
from platform_developer.store import FlagStore, InvalidInput


class _NoDatabase:
    def ready(self):
        return False

    def close(self):
        pass

    def transaction(self, workspace):
        raise AssertionError('database must not be reached')


@pytest.fixture
def client():
    verifier, headers = auth()
    with TestClient(create_app(_NoDatabase(), verifier)) as c:
        yield c, headers('flags:read flags:write', uuid4())


def test_invalid_input_is_a_value_error():
    assert issubclass(InvalidInput, ValueError)


@pytest.mark.parametrize('call', [
    lambda: store_module.identifier('Bad Name'),
    lambda: store_module.subject('bad subject!'),
    lambda: FlagStore(_NoDatabase()).list(uuid4(), 0),
    lambda: FlagStore(_NoDatabase()).put(uuid4(), 'ok', True, 10001, [], None),
    lambda: FlagStore(_NoDatabase()).put(uuid4(), 'ok', True, 0, ['ok'] * 101, None),
])
def test_store_validation_raises_invalid_input(call):
    with pytest.raises(InvalidInput):
        call()


def test_domain_validation_returns_422(client):
    c, h = client
    response = c.get('/v1/flags/Bad', headers=h)
    assert response.status_code == 422
    assert response.json() == {'detail': 'Invalid input'}
    response = c.post('/v1/flags/ok/evaluate', headers=h, json={'subject': 'bad subject!'})
    assert response.status_code == 422


def test_unexpected_value_error_is_redacted_500(client, monkeypatch):
    def broken(self, workspace, limit=100, after=''):
        raise ValueError('secret-bearing internal detail')

    monkeypatch.setattr(FlagStore, 'list', broken)
    c, h = client
    response = c.get('/v1/flags', headers=h)
    assert response.status_code == 500
    assert 'secret-bearing' not in response.text
    assert response.json() == {'detail': 'internal server error'}
