from types import SimpleNamespace

import pytest

import pytidb.client as client_mod
from pytidb.ext.mcp import server as mcp_server


class _IdentifierPreparer:
    def quote(self, value: str) -> str:
        return value


class FakeEngine:
    def __init__(self, host: str):
        self.url = SimpleNamespace(host=host)
        self.dialect = SimpleNamespace(identifier_preparer=_IdentifierPreparer())

    def dispose(self) -> None:
        pass


@pytest.fixture(scope="session", autouse=True)
def shared_client():
    """Override heavy shared_client fixture from tests/conftest.py."""
    yield None


@pytest.fixture(scope="session", autouse=True)
def text_embed():
    """Override embedding fixture to prevent network calls."""
    yield None


@pytest.mark.asyncio
async def test_app_lifespan_passes_ca_path(monkeypatch):
    captured_kwargs: dict = {}

    class DummyConnector:
        def __init__(self, *args, **kwargs):
            captured_kwargs.update(kwargs)
            self.host = kwargs.get("host", "127.0.0.1")
            self.port = kwargs.get("port", 4000)
            self.database = kwargs.get("database", "test")

        def disconnect(self):
            captured_kwargs["disconnected"] = True

    monkeypatch.setenv("TIDB_CA_PATH", "/tmp/isrgrootx1.pem")
    monkeypatch.setattr(mcp_server, "TiDBConnector", DummyConnector)

    async with mcp_server.app_lifespan(object()):
        pass

    assert captured_kwargs["ca_path"] == "/tmp/isrgrootx1.pem"
    assert captured_kwargs.get("disconnected") is True


def test_tidb_client_connect_applies_ca_path(monkeypatch):
    recorded: dict = {}
    target_host = "custom.tidb.local"

    def fake_build_tidb_connection_url(
        schema="mysql+pymysql",
        host="localhost",
        port=4000,
        username="root",
        password="",
        database="test",
        enable_ssl=None,
    ):
        recorded["enable_ssl"] = enable_ssl
        return f"{schema}://{username}@{host}:{port}/{database}"

    def fake_create_engine(url, **kwargs):
        recorded["engine_kwargs"] = kwargs
        recorded["engine_url"] = url
        return FakeEngine(target_host)

    monkeypatch.setattr(
        client_mod, "build_tidb_connection_url", fake_build_tidb_connection_url
    )
    monkeypatch.setattr(client_mod, "create_engine", fake_create_engine)

    client = client_mod.TiDBClient.connect(
        host=target_host,
        ca_path="/tmp/isrgrootx1.pem",
    )

    try:
        assert recorded["enable_ssl"] is True
        assert (
            recorded["engine_kwargs"]["connect_args"]["ssl"]["ca"]
            == "/tmp/isrgrootx1.pem"
        )
    finally:
        client.disconnect()


def test_tidb_client_connect_without_ca_path_leaves_ssl_unset(monkeypatch):
    recorded: dict = {}
    target_host = "custom.tidb.local"

    def fake_build_tidb_connection_url(
        schema="mysql+pymysql",
        host="localhost",
        port=4000,
        username="root",
        password="",
        database="test",
        enable_ssl=None,
    ):
        recorded["enable_ssl"] = enable_ssl
        return f"{schema}://{username}@{host}:{port}/{database}"

    def fake_create_engine(url, **kwargs):
        recorded["engine_kwargs"] = kwargs
        return FakeEngine(target_host)

    monkeypatch.setattr(
        client_mod, "build_tidb_connection_url", fake_build_tidb_connection_url
    )
    monkeypatch.setattr(client_mod, "create_engine", fake_create_engine)

    client = client_mod.TiDBClient.connect(host=target_host)

    try:
        assert recorded["enable_ssl"] is None
        assert "connect_args" not in recorded["engine_kwargs"]
    finally:
        client.disconnect()
