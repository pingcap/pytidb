from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from pytidb.ext.mcp import server


class DummyTiDBClient:
    def __init__(self):
        pass

    def disconnect(self):
        pass

    def session(self):
        return nullcontext()

    def query(self, *args, **kwargs):
        return SimpleNamespace(to_list=lambda: [], scalar=lambda: "")

    def execute(self, *args, **kwargs):
        return SimpleNamespace(model_dump=lambda: {})

    def list_tables(self):
        return []


@pytest.fixture
def capture_connect(monkeypatch):
    calls = []

    class FakeTiDBClient:
        @classmethod
        def connect(cls, **kwargs):
            calls.append(kwargs)
            return DummyTiDBClient()

    monkeypatch.setattr(server, "TiDBClient", FakeTiDBClient)
    return calls


def test_tidb_connector_passes_ca_path_to_ssl(capture_connect, tmp_path):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_text("CERT")

    connector = server.TiDBConnector(
        host="localhost",
        port=4000,
        username="root",
        password="password",
        database="test",
        ca_cert_path=str(ca_file),
    )

    assert capture_connect[0]["connect_args"]["ssl"]["ca"] == str(ca_file)

    connector.switch_database("another_db")
    assert capture_connect[1]["connect_args"]["ssl"]["ca"] == str(ca_file)


def test_tidb_connector_omits_ssl_when_no_ca(capture_connect):
    server.TiDBConnector(
        host="localhost",
        port=4000,
        username="root",
        password="password",
        database="test",
    )

    assert "connect_args" not in capture_connect[0]


def test_resolve_ca_path_handles_invalid_file(tmp_path):
    missing = tmp_path / "missing.pem"
    with pytest.raises(ValueError):
        server.resolve_ca_path(str(missing))


def test_resolve_ca_path_returns_valid_path(tmp_path):
    ca_file = tmp_path / "ca.pem"
    ca_file.write_text("CERT")

    result = server.resolve_ca_path(str(ca_file))
    assert result == str(ca_file)


@pytest.mark.asyncio
async def test_app_lifespan_raises_when_invalid_ca(monkeypatch, tmp_path):
    missing = tmp_path / "missing.pem"
    monkeypatch.setenv("TIDB_CA_PATH", str(missing))

    with pytest.raises(ValueError):
        async with server.app_lifespan(server.mcp):
            pass
