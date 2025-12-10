import copy
import ssl
from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from pytidb.client import TiDBClient


class DummyEngine:
    def __init__(self, url, **kwargs):
        self.url = make_url(url)
        self.kwargs = kwargs
        self.dialect = SimpleNamespace(identifier_preparer=object())
        self.disposed = False

    def dispose(self):
        self.disposed = True


@pytest.fixture(scope="session", autouse=True)
def shared_client():
    """Override the integration shared_client fixture for these unit tests."""
    yield


def _patch_create_engine(monkeypatch):
    created = []

    def _fake_create_engine(url, **kwargs):
        engine = DummyEngine(url, **kwargs)
        created.append(engine)
        return engine

    monkeypatch.setattr("pytidb.client.create_engine", _fake_create_engine)
    return created


def _connect_kwargs():
    return dict(
        host="gateway01.us-east-1.prod.aws.tidbcloud.com",
        port=4000,
        username="test_user",
        password="secret",
        database="testdb",
    )


def test_tidb_client_connect_injects_ssl_ca_path(monkeypatch):
    _patch_create_engine(monkeypatch)
    client = TiDBClient.connect(ca_path="/tmp/isrgrootx1.pem", **_connect_kwargs())
    connect_args = client.db_engine.kwargs.get("connect_args")
    assert connect_args == {"ssl": {"ca": "/tmp/isrgrootx1.pem"}}


def test_tidb_client_connect_merges_existing_connect_args(monkeypatch):
    _patch_create_engine(monkeypatch)
    existing_connect_args = {
        "charset": "utf8mb4",
        "ssl": {"cert": "/tmp/client-cert.pem"},
    }
    snapshot = copy.deepcopy(existing_connect_args)
    client = TiDBClient.connect(
        ca_path="/tmp/isrgrootx1.pem",
        connect_args=existing_connect_args,
        **_connect_kwargs(),
    )

    connect_args = client.db_engine.kwargs.get("connect_args")
    assert connect_args["charset"] == "utf8mb4"
    assert connect_args["ssl"]["cert"] == "/tmp/client-cert.pem"
    assert connect_args["ssl"]["ca"] == "/tmp/isrgrootx1.pem"
    assert existing_connect_args == snapshot
    assert connect_args["ssl"] is not existing_connect_args["ssl"]


def test_tidb_client_connect_preserves_ssl_context_object(monkeypatch):
    _patch_create_engine(monkeypatch)
    ssl_context = ssl.create_default_context()
    existing_connect_args = {"ssl": ssl_context}

    client = TiDBClient.connect(
        ca_path="/tmp/isrgrootx1.pem",
        connect_args=existing_connect_args,
        **_connect_kwargs(),
    )

    connect_args = client.db_engine.kwargs.get("connect_args")
    assert connect_args is not existing_connect_args
    assert connect_args["ssl"] is ssl_context


def test_tidb_client_connect_without_ca_path_keeps_connect_args_untouched(
    monkeypatch,
):
    _patch_create_engine(monkeypatch)
    client = TiDBClient.connect(**_connect_kwargs())
    assert "connect_args" not in client.db_engine.kwargs
