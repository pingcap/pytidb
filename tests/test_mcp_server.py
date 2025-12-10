import pytest
from pytidb.ext.mcp import server as mcp_server


@pytest.mark.asyncio
async def test_app_lifespan_reads_tidb_ca_path(monkeypatch):
    fake_ca_path = "/tmp/isrgrootx1.pem"
    monkeypatch.setenv("TIDB_CA_PATH", fake_ca_path)

    captured_kwargs = {}

    class DummyConnector:
        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)
            self.host = "localhost"
            self.port = 4000
            self.database = "test"

        def disconnect(self):
            captured_kwargs["disconnect_called"] = True

    monkeypatch.setattr(mcp_server, "TiDBConnector", DummyConnector)

    class DummyApp:
        pass

    async with mcp_server.app_lifespan(DummyApp()):
        pass

    assert captured_kwargs.get("ca_path") == fake_ca_path
