from unittest.mock import Mock

import pytest

pytest.importorskip("mcp.server.fastmcp")

import pytidb.ext.mcp as mcp_cli
import pytidb.ext.mcp.server as mcp_server


def test_mcp_cli_forwards_query_timeout(monkeypatch):
    captured = {}

    class DummyServer:
        def run(self, transport):
            captured["transport"] = transport

    def fake_create_mcp_server(**kwargs):
        captured.update(kwargs)
        return DummyServer()

    monkeypatch.setattr(mcp_cli, "create_mcp_server", fake_create_mcp_server)

    callback = mcp_cli.main.callback
    assert callback is not None

    callback(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        query_timeout=12,
    )

    assert captured == {
        "host": "127.0.0.1",
        "port": 8000,
        "stateless_http": True,
        "query_timeout": 12,
        "transport": "streamable-http",
    }


def test_tidb_connector_sets_query_timeout_init_command(monkeypatch):
    calls = []

    def fake_connect(**kwargs):
        calls.append(kwargs)
        return Mock()

    monkeypatch.setattr(mcp_server.TiDBClient, "connect", staticmethod(fake_connect))

    mcp_server.TiDBConnector(
        host="127.0.0.1",
        port=4000,
        username="root",
        password="",
        database="test",
        query_timeout=7,
    )

    assert calls == [
        {
            "url": None,
            "host": "127.0.0.1",
            "port": 4000,
            "username": "root",
            "password": "",
            "database": "test",
            "connect_args": {
                "init_command": "SET SESSION max_execution_time = 7000"
            },
        }
    ]


def test_tidb_connector_preserves_query_timeout_when_switching_databases(monkeypatch):
    calls = []

    def fake_connect(**kwargs):
        client = Mock()
        client.disconnect = Mock()
        calls.append(kwargs)
        return client

    monkeypatch.setattr(mcp_server.TiDBClient, "connect", staticmethod(fake_connect))

    connector = mcp_server.TiDBConnector(
        host="127.0.0.1",
        port=4000,
        username="root",
        password="",
        database="test",
        query_timeout=9,
    )

    connector.switch_database("analytics")

    assert calls[1] == {
        "url": None,
        "host": "127.0.0.1",
        "port": 4000,
        "username": "root",
        "password": "",
        "database": "analytics",
        "connect_args": {
            "init_command": "SET SESSION max_execution_time = 9000"
        },
    }


def test_create_app_lifespan_passes_query_timeout(monkeypatch):
    captured = {}

    class FakeConnector:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.host = kwargs["host"]
            self.port = kwargs["port"]
            self.database = kwargs["database"]

        def disconnect(self):
            captured["disconnected"] = True

    monkeypatch.setattr(mcp_server, "TiDBConnector", FakeConnector)

    lifespan = mcp_server.create_app_lifespan(15)

    async def run_lifespan():
        async with lifespan(Mock()):
            pass

    import asyncio

    asyncio.run(run_lifespan())

    assert captured["query_timeout"] == 15
    assert captured["disconnected"] is True
