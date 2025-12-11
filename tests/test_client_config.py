from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from pytidb import TiDBClient


class DummyEngine:
    def __init__(self, url: str):
        self.url = make_url(url)
        identifier_preparer = SimpleNamespace(quote=lambda _self, ident: ident)
        self.dialect = SimpleNamespace(identifier_preparer=identifier_preparer)

    def dispose(self) -> None:  # pragma: no cover - the tests never dispose
        pass


@pytest.fixture(scope="session", autouse=True)
def shared_client():
    """Override the global shared_client fixture so unit tests don't hit a real DB."""
    yield


@pytest.fixture(scope="session", autouse=True)
def text_embed():
    """Override the autouse text_embed fixture from tests/conftest.py."""
    yield


@pytest.fixture
def create_engine_spy(monkeypatch):
    calls: dict[str, object] = {}

    def fake_create_engine(url, **kwargs):
        calls["url"] = url
        calls["kwargs"] = kwargs
        return DummyEngine(url)

    monkeypatch.setattr("pytidb.client.create_engine", fake_create_engine)
    return calls


def test_connect_injects_ssl_ca_from_env(monkeypatch, create_engine_spy):
    monkeypatch.setenv("TIDB_CA_PATH", "/tmp/isrg-root.pem")

    TiDBClient.connect()

    connect_args = create_engine_spy["kwargs"]["connect_args"]
    assert connect_args["ssl"]["ca"] == "/tmp/isrg-root.pem"


def test_connect_uses_explicit_ca_path_without_env(create_engine_spy):
    TiDBClient.connect(ca_path="/tmp/custom-ca.pem")

    connect_args = create_engine_spy["kwargs"]["connect_args"]
    assert connect_args["ssl"]["ca"] == "/tmp/custom-ca.pem"


def test_connect_does_not_set_ssl_when_no_ca_path(monkeypatch, create_engine_spy):
    monkeypatch.delenv("TIDB_CA_PATH", raising=False)

    TiDBClient.connect()

    assert "connect_args" not in create_engine_spy["kwargs"]


def test_connect_merges_existing_connect_args(monkeypatch, create_engine_spy):
    monkeypatch.setenv("TIDB_CA_PATH", "/tmp/isrg-root.pem")
    original_connect_args = {
        "charset": "utf8mb4",
        "ssl": {"cert": "/tmp/client-cert.pem"},
    }

    TiDBClient.connect(connect_args=original_connect_args)

    # Original dict should not be mutated.
    assert original_connect_args == {
        "charset": "utf8mb4",
        "ssl": {"cert": "/tmp/client-cert.pem"},
    }

    connect_args = create_engine_spy["kwargs"]["connect_args"]
    assert connect_args["charset"] == "utf8mb4"
    assert connect_args["ssl"]["cert"] == "/tmp/client-cert.pem"
    assert connect_args["ssl"]["ca"] == "/tmp/isrg-root.pem"
