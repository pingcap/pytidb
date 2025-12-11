from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from pytidb.client import TiDBClient
from pytidb.ext.mcp import server as mcp_server


class DummyEngine:
    def __init__(self, url: str):
        self.url = make_url(url)
        self.dialect = SimpleNamespace(identifier_preparer=None)

    def dispose(self):
        pass


class DummyTiDBClient:
    def disconnect(self):
        pass


def test_tidb_client_connect_injects_ssl_ca(monkeypatch, tmp_path):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_text("dummy")
    captured_kwargs: dict = {}

    def fake_create_engine(url, echo=None, **kwargs):
        captured_kwargs.update(kwargs)
        return DummyEngine(url)

    monkeypatch.setattr("pytidb.client.create_engine", fake_create_engine)

    TiDBClient.connect(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="secret",
        database="test",
        ca_path=str(ca_file),
    )

    assert captured_kwargs["connect_args"]["ssl"]["ca"] == str(ca_file)


def test_tidb_client_connect_missing_ca_file(monkeypatch, tmp_path):
    missing_ca = tmp_path / "missing.pem"

    def fail_create_engine(*_args, **_kwargs):
        pytest.fail("create_engine should not be called when CA path is invalid")

    monkeypatch.setattr("pytidb.client.create_engine", fail_create_engine)

    with pytest.raises(FileNotFoundError):
        TiDBClient.connect(host="localhost", ca_path=str(missing_ca))


def test_tidb_connector_uses_tidb_ca_path_env(monkeypatch, tmp_path):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_text("dummy")
    captured_kwargs: dict = {}

    def fake_connect(cls, **kwargs):
        captured_kwargs.update(kwargs)
        return DummyTiDBClient()

    monkeypatch.setattr(
        mcp_server.TiDBClient, "connect", classmethod(fake_connect)
    )
    monkeypatch.setenv("TIDB_CA_PATH", str(ca_file))

    mcp_server.TiDBConnector(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        port=4000,
        username="user.root",
        password="secret",
        database="test",
    )

    assert captured_kwargs["ca_path"] == str(ca_file)


def test_tidb_connector_without_ca_env(monkeypatch):
    captured_kwargs: dict = {}

    def fake_connect(cls, **kwargs):
        captured_kwargs.update(kwargs)
        return DummyTiDBClient()

    monkeypatch.setattr(
        mcp_server.TiDBClient, "connect", classmethod(fake_connect)
    )
    monkeypatch.delenv("TIDB_CA_PATH", raising=False)

    mcp_server.TiDBConnector(
        host="localhost",
        port=4000,
        username="root",
        password="",
        database="test",
    )

    assert "ca_path" not in captured_kwargs
