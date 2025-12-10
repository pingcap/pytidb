from types import SimpleNamespace

import pytest

import pytidb.client as client_module
from pytidb.client import TiDBClient
from pytidb.ext.mcp.server import TiDBConnector


class DummyEngine:
    def __init__(self, host: str):
        self.url = SimpleNamespace(host=host)
        self.dialect = SimpleNamespace(identifier_preparer=object())

    def dispose(self):
        pass


def _patch_create_engine(monkeypatch, *, host: str, captured: dict):
    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return DummyEngine(host)

    monkeypatch.setattr(client_module, "create_engine", fake_create_engine)


@pytest.fixture
def captured_engine_args():
    return {}


def test_tidb_client_connect_sets_ssl_ca(monkeypatch, captured_engine_args):
    host = "gateway01.us-west-2.prod.aws.tidbcloud.com"
    _patch_create_engine(monkeypatch, host=host, captured=captured_engine_args)

    TiDBClient.connect(
        host=host,
        username="user",
        password="password",
        database="test",
        ca_path="/tmp/isrgrootx1.pem",
    )

    assert captured_engine_args["kwargs"]["connect_args"]["ssl"]["ca"] == "/tmp/isrgrootx1.pem"


def test_tidb_client_connect_merges_existing_connect_args(monkeypatch, captured_engine_args):
    host = "gateway01.us-west-2.prod.aws.tidbcloud.com"
    _patch_create_engine(monkeypatch, host=host, captured=captured_engine_args)

    initial_connect_args = {"ssl": {"cert": "/tmp/client-cert.pem"}, "charset": "utf8mb4"}

    TiDBClient.connect(
        host=host,
        username="user",
        password="password",
        database="test",
        ca_path="C:/certs/isrgrootx1.pem",
        connect_args=initial_connect_args,
    )

    ssl_args = captured_engine_args["kwargs"]["connect_args"]["ssl"]
    assert ssl_args["ca"] == "C:/certs/isrgrootx1.pem"
    assert ssl_args["cert"] == "/tmp/client-cert.pem"
    assert captured_engine_args["kwargs"]["connect_args"]["charset"] == "utf8mb4"
    # Original dict should stay untouched to avoid leaking state back to callers.
    assert "ca" not in initial_connect_args["ssl"]


def test_tidb_client_connect_without_ca_path_leaves_connect_args_unchanged(
    monkeypatch, captured_engine_args
):
    host = "gateway01.us-west-2.prod.aws.tidbcloud.com"
    _patch_create_engine(monkeypatch, host=host, captured=captured_engine_args)

    TiDBClient.connect(
        host=host,
        username="user",
        password="password",
        database="test",
    )

    assert "connect_args" not in captured_engine_args["kwargs"]


def test_tidb_connector_reuses_ca_path(monkeypatch):
    calls = []

    def fake_connect(cls, **kwargs):
        calls.append(kwargs.get("ca_path"))
        return object()

    monkeypatch.setattr(TiDBClient, "connect", classmethod(fake_connect))

    connector = TiDBConnector(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        port=4000,
        username="user",
        password="password",
        database="test",
        ca_path="/tmp/custom-ca.pem",
    )

    assert calls == ["/tmp/custom-ca.pem"]

    connector.switch_database("another_db")

    assert calls == ["/tmp/custom-ca.pem", "/tmp/custom-ca.pem"]
