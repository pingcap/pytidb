from unittest.mock import MagicMock

import pytest

from pytidb import client as client_module
from pytidb.client import AsyncTiDBClient, TiDBClient
from pytidb.table import Table


@pytest.mark.asyncio
async def test_async_client_connect_and_disconnect(monkeypatch):
    sync_client = MagicMock(spec=TiDBClient)
    sync_client.db_engine = object()
    sync_client.is_serverless = True

    calls = []

    async def fake_run_sync(func, *args, **kwargs):
        calls.append((func, args, kwargs))
        if func is TiDBClient.connect:
            return sync_client
        return func(*args, **kwargs)

    monkeypatch.setattr(client_module, "run_sync", fake_run_sync)

    client = await AsyncTiDBClient.connect(host="example", database="demo")

    assert client.sync_client is sync_client
    assert client.db_engine is sync_client.db_engine
    assert client.is_serverless is True

    await client.disconnect()

    assert sync_client.disconnect.called
    assert calls[0][0] is TiDBClient.connect
    assert calls[0][2]["host"] == "example"
    assert calls[0][2]["database"] == "demo"
    assert calls[1][0] is sync_client.disconnect


@pytest.mark.asyncio
async def test_async_client_context_manager_disconnects(monkeypatch):
    sync_client = MagicMock(spec=TiDBClient)

    async def fake_run_sync(func, *args, **kwargs):
        if func is TiDBClient.connect:
            return sync_client
        return func(*args, **kwargs)

    monkeypatch.setattr(client_module, "run_sync", fake_run_sync)

    async with AsyncTiDBClient.connect(url="mysql://root@localhost:4000/test") as client:
        assert client.sync_client is sync_client

    sync_client.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_async_client_method_proxies(monkeypatch):
    sync_client = MagicMock(spec=TiDBClient)
    sync_client.db_engine = object()
    sync_client.is_serverless = False

    fake_table = MagicMock(spec=Table)
    sync_client.create_table.return_value = fake_table
    sync_client.open_table.return_value = fake_table
    sync_client.execute.return_value = "executed"
    sync_client.query.return_value = "queried"
    sync_client.create_database.return_value = "created"
    sync_client.list_databases.return_value = ["db1"]
    sync_client.list_tables.return_value = ["table1"]
    sync_client.current_database.return_value = "db1"
    sync_client.configure_embedding_provider.return_value = "configured"

    async def fake_run_sync(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(client_module, "run_sync", fake_run_sync)

    client = AsyncTiDBClient(sync_client)

    assert await client.create_database("foo") == "created"
    sync_client.create_database.assert_called_once_with("foo", if_exists="raise")

    await client.drop_database("bar")
    sync_client.drop_database.assert_called_once_with("bar")

    assert await client.list_databases() == ["db1"]
    sync_client.list_databases.assert_called_once_with()

    assert await client.current_database() == "db1"
    sync_client.current_database.assert_called_once_with()

    assert await client.list_tables() == ["table1"]
    sync_client.list_tables.assert_called_once_with()

    assert await client.has_database("foo") == sync_client.has_database.return_value
    sync_client.has_database.assert_called_once_with("foo")

    assert await client.has_table("tab") == sync_client.has_table.return_value
    sync_client.has_table.assert_called_once_with("tab")

    await client.use_database("alt", ensure_db=True)
    sync_client.use_database.assert_called_once_with("alt", ensure_db=True)

    await client.drop_table("tab", if_not_exists="skip")
    sync_client.drop_table.assert_called_once_with("tab", if_not_exists="skip")

    assert await client.execute("SELECT 1") == "executed"
    sync_client.execute.assert_called_once_with("SELECT 1", None, raise_error=False)

    assert await client.query("SELECT 1") == "queried"
    sync_client.query.assert_called_once_with("SELECT 1", None)

    assert await client.configure_embedding_provider("openai", "key") == "configured"
    sync_client.configure_embedding_provider.assert_called_once_with("openai", "key")

    assert await client.create_table(schema="schema") is fake_table
    sync_client.create_table.assert_called_once_with(schema="schema", if_exists="raise")

    assert await client.open_table("table1") is fake_table
    sync_client.open_table.assert_called_once_with("table1")
