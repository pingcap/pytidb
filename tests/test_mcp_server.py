import asyncio

import pytest

from pytidb.ext.mcp import server as mcp_server


@pytest.fixture(scope="session", autouse=True)
def shared_client():
    """Override the integration shared_client fixture for pure unit tests."""
    yield


def _run_lifespan(monkeypatch, *, ca_path_env: str | None):
    created_connectors = []

    class DummyConnector:
        def __init__(
            self,
            database_url=None,
            *,
            host=None,
            port=None,
            username=None,
            password=None,
            database=None,
            ca_path=None,
        ):
            self.database_url = database_url
            self.host = host
            self.port = port
            self.username = username
            self.password = password
            self.database = database
            self.ca_path = ca_path
            self.disconnect_called = False
            created_connectors.append(self)

        def disconnect(self):
            self.disconnect_called = True

    monkeypatch.setattr(mcp_server, "TiDBConnector", DummyConnector)

    if ca_path_env is None:
        monkeypatch.delenv("TIDB_CA_PATH", raising=False)
    else:
        monkeypatch.setenv("TIDB_CA_PATH", ca_path_env)

    async def _main():
        async with mcp_server.app_lifespan(None) as ctx:
            assert ctx.tidb is created_connectors[0]

    asyncio.run(_main())
    assert created_connectors, "TiDBConnector was never constructed"
    connector = created_connectors[0]
    assert connector.disconnect_called
    return connector


def test_app_lifespan_passes_tidb_ca_path(monkeypatch):
    connector = _run_lifespan(monkeypatch, ca_path_env="/tmp/isrgrootx1.pem")
    assert connector.ca_path == "/tmp/isrgrootx1.pem"


def test_app_lifespan_without_tidb_ca_path(monkeypatch):
    connector = _run_lifespan(monkeypatch, ca_path_env=None)
    assert connector.ca_path is None
