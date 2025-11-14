"""
Unit tests for async client functionality.

Using pytest-asyncio for async test support.
"""

import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import pytest

from pytidb import TiDBClient
from pytidb.async_client import AsyncTiDBClient, AsyncTable
from pytidb.schema import TableModel, Field


class TestAsyncTiDBClient:
    """Test AsyncTiDBClient class."""

    @pytest.mark.asyncio
    async def test_async_client_creation(self):
        """Test creating AsyncTiDBClient from TiDBClient."""
        mock_engine = MagicMock()
        mock_engine.url.host = "localhost"
        reconnect_params = {"debug": False}

        sync_client = TiDBClient(mock_engine, reconnect_params)
        async_client = AsyncTiDBClient(sync_client)

        assert async_client._sync_client == sync_client
        assert async_client.db_engine == mock_engine
        assert async_client._reconnect_params == reconnect_params

    @pytest.mark.asyncio
    async def test_async_connect_classmethod(self):
        """Test AsyncTiDBClient.connect() class method."""
        with patch("pytidb.async_client.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_engine.url.host = "localhost"
            mock_create_engine.return_value = mock_engine

            async_client = await AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            )

            assert isinstance(async_client, AsyncTiDBClient)
            assert async_client._sync_client is not None
            assert async_client._sync_client._db_engine == mock_engine

    @pytest.mark.asyncio
    async def test_async_execute_success(self):
        """Test async execute with successful result."""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 3
        mock_result.success = True
        mock_client.execute.return_value = mock_result

        async_client = AsyncTiDBClient(mock_client)
        result = await async_client.execute("INSERT INTO test VALUES (1, 2, 3)")

        mock_client.execute.assert_called_once()
        assert result.rowcount == 3
        assert result.success is True

    @pytest.mark.asyncio
    async def test_async_execute_failure(self):
        """Test async execute with error handling."""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_result.success = False
        mock_result.message = "Table already exists"
        mock_client.execute.return_value = mock_result

        async_client = AsyncTiDBClient(mock_client)
        result = await async_client.execute("CREATE TABLE test (id int)")

        assert result.rowcount == 0
        assert result.success is False
        assert result.message == "Table already exists"

    @pytest.mark.asyncio
    async def test_async_query_raw_sql(self):
        """Test async query with raw SQL."""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_result.to_list.return_value = [{"id": 1}, {"id": 2}, {"id": 3}]
        mock_client.query.return_value = mock_result

        async_client = AsyncTiDBClient(mock_client)
        result = await async_client.query("SELECT id FROM test")

        mock_client.query.assert_called_once()
        assert result == mock_result

    @pytest.mark.asyncio
    async def test_async_create_database(self):
        """Test async create_database."""
        mock_client = MagicMock()
        async_client = AsyncTiDBClient(mock_client)

        await async_client.create_database("test_db", if_exists="raise")

        mock_client.create_database.assert_called_once_with("test_db", if_exists="raise")

    @pytest.mark.asyncio
    async def test_async_drop_database(self):
        """Test async drop_database."""
        mock_client = MagicMock()
        async_client = AsyncTiDBClient(mock_client)

        await async_client.drop_database("test_db")

        mock_client.drop_database.assert_called_once_with("test_db")

    @pytest.mark.asyncio
    async def test_async_list_databases(self):
        """Test async list_databases."""
        mock_client = MagicMock()
        mock_client.list_databases.return_value = ["test_db", "mysql", "information_schema"]
        async_client = AsyncTiDBClient(mock_client)

        result = await async_client.list_databases()

        assert result == ["test_db", "mysql", "information_schema"]
        mock_client.list_databases.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_has_database(self):
        """Test async has_database."""
        mock_client = MagicMock()
        mock_client.has_database.return_value = True
        async_client = AsyncTiDBClient(mock_client)

        result = await async_client.has_database("test_db")

        assert result is True
        mock_client.has_database.assert_called_once_with("test_db")

    @pytest.mark.asyncio
    async def test_async_current_database(self):
        """Test async current_database."""
        mock_client = MagicMock()
        mock_client.current_database.return_value = "test_db"
        async_client = AsyncTiDBClient(mock_client)

        result = await async_client.current_database()

        assert result == "test_db"
        mock_client.current_database.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_use_database(self):
        """Test async use_database."""
        mock_client = MagicMock()
        async_client = AsyncTiDBClient(mock_client)

        await async_client.use_database("new_db")

        mock_client.use_database.assert_called_once_with("new_db", ensure_db=None)

    @pytest.mark.asyncio
    async def test_async_list_tables(self):
        """Test async list_tables."""
        mock_client = MagicMock()
        mock_client.list_tables.return_value = ["table1", "table2"]
        async_client = AsyncTiDBClient(mock_client)

        result = await async_client.list_tables()

        assert result == ["table1", "table2"]
        mock_client.list_tables.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_has_table(self):
        """Test async has_table."""
        mock_client = MagicMock()
        mock_client.has_table.return_value = True
        async_client = AsyncTiDBClient(mock_client)

        result = await async_client.has_table("test_table")

        assert result is True
        mock_client.has_table.assert_called_once_with("test_table")

    @pytest.mark.asyncio
    async def test_async_disconnect(self):
        """Test async disconnect."""
        mock_client = MagicMock()
        async_client = AsyncTiDBClient(mock_client)

        await async_client.disconnect()

        mock_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_configure_embedding_provider(self):
        """Test async configure_embedding_provider."""
        mock_client = MagicMock()
        mock_result = MagicMock()
        mock_client.configure_embedding_provider.return_value = mock_result
        async_client = AsyncTiDBClient(mock_client)

        result = await async_client.configure_embedding_provider("openai", "test-key")

        mock_client.configure_embedding_provider.assert_called_once_with("openai", "test-key")
        assert result == mock_result


class TestAsyncTable:
    """Test AsyncTable class."""

    @pytest.mark.asyncio
    async def test_async_table_creation(self):
        """Test creating AsyncTable."""
        mock_client = MagicMock()
        mock_engine = MagicMock()
        mock_engine.dialect.identifier_preparer = MagicMock()
        mock_client.db_engine = mock_engine

        class TestSchema(TableModel):
            __tablename__ = "test_table"
            id: int = Field(primary_key=True)
            name: str = Field()

        async_table = AsyncTable(schema=TestSchema, client=mock_client)

        assert async_table._sync_table is not None
        assert async_table._sync_table._table_model == TestSchema

    @pytest.mark.asyncio
    async def test_async_table_insert(self):
        """Test async insert."""
        mock_table = MagicMock()
        mock_result = MagicMock()
        mock_result.id = 1
        mock_result.name = "test"
        mock_table.insert.return_value = mock_result

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.insert({"id": 1, "name": "test"})

        mock_table.insert.assert_called_once()
        assert result.id == 1
        assert result.name == "test"

    @pytest.mark.asyncio
    async def test_async_table_bulk_insert(self):
        """Test async bulk_insert."""
        mock_table = MagicMock()
        mock_result = [MagicMock(), MagicMock()]
        mock_result[0].id = 1
        mock_result[1].id = 2
        mock_table.bulk_insert.return_value = mock_result

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.bulk_insert([{"id": 1}, {"id": 2}])

        mock_table.bulk_insert.assert_called_once()
        assert len(result) == 2
        assert result[0].id == 1

    @pytest.mark.asyncio
    async def test_async_table_update(self):
        """Test async update."""
        mock_table = MagicMock()
        async_table = AsyncTable(sync_table=mock_table)

        await async_table.update({"name": "updated"}, {"id": 1})

        mock_table.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_table_delete(self):
        """Test async delete."""
        mock_table = MagicMock()
        async_table = AsyncTable(sync_table=mock_table)

        await async_table.delete({"id": 1})

        mock_table.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_table_truncate(self):
        """Test async truncate."""
        mock_table = MagicMock()
        async_table = AsyncTable(sync_table=mock_table)

        await async_table.truncate()

        mock_table.truncate.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_table_get(self):
        """Test async get by ID."""
        mock_table = MagicMock()
        mock_result = MagicMock()
        mock_result.id = 1
        mock_table.get.return_value = mock_result

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.get(1)

        mock_table.get.assert_called_once_with(1)
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_async_table_query(self):
        """Test async query."""
        mock_table = MagicMock()
        mock_result = MagicMock()
        mock_result.to_list.return_value = [{"id": 1}, {"id": 2}]
        mock_table.query.return_value = mock_result

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.query()

        mock_table.query.assert_called_once()
        assert result == mock_result

    @pytest.mark.asyncio
    async def test_async_table_rows(self):
        """Test async rows count."""
        mock_table = MagicMock()
        mock_table.rows.return_value = 42

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.rows()

        assert result == 42
        mock_table.rows.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_table_columns(self):
        """Test async columns info."""
        mock_table = MagicMock()
        mock_columns = [{"column_name": "id", "column_type": "int"}]
        mock_table.columns.return_value = mock_columns

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.columns()

        assert result == mock_columns
        mock_table.columns.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_table_create(self):
        """Test async create table."""
        mock_table = MagicMock()
        mock_table.create.return_value = mock_table

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.create()

        mock_table.create.assert_called_once()
        assert result == async_table

    @pytest.mark.asyncio
    async def test_async_table_drop(self):
        """Test async drop table."""
        mock_table = MagicMock()
        async_table = AsyncTable(sync_table=mock_table)

        await async_table.drop()

        mock_table.drop.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_table_search(self):
        """Test async search."""
        mock_table = MagicMock()
        mock_search = MagicMock()
        mock_table.search.return_value = mock_search

        async_table = AsyncTable(sync_table=mock_table)
        result = await async_table.search("test query")

        mock_table.search.assert_called_once()
        assert result == mock_search


class TestAsyncContextManagers:
    """Test async context managers."""

    @pytest.mark.asyncio
    async def test_async_client_as_context_manager(self):
        """Test using AsyncTiDBClient as async context manager."""
        with patch("pytidb.async_client.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_engine.url.host = "localhost"
            mock_create_engine.return_value = mock_engine

            async with AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            ) as client:
                assert isinstance(client, AsyncTiDBClient)
                assert client.db_engine == mock_engine

            # Verify disconnect was called
            mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_disconnect_on_context_exit(self):
        """Test that disconnect is called when exiting context manager."""
        with patch("pytidb.async_client.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_engine.url.host = "localhost"
            mock_create_engine.return_value = mock_engine

            async with AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            ) as client:
                pass

            # Verify engine.dispose was called
            mock_engine.dispose.assert_called_once()


class TestAsyncConcurrency:
    """Test concurrent async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_queries(self):
        """Test concurrent queries don't block each other."""
        mock_client = MagicMock()
        mock_results = []

        def slow_query(*args, **kwargs):
            import time
            time.sleep(0.1)  # Simulate slow query
            result = MagicMock()
            result.scalar.return_value = 42
            return result

        mock_client.query.side_effect = slow_query

        async_client = AsyncTiDBClient(mock_client)

        # Run multiple queries concurrently
        tasks = [
            async_client.query("SELECT 1"),
            async_client.query("SELECT 2"),
            async_client.query("SELECT 3"),
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert mock_client.query.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_operations_mix(self):
        """Test mix of concurrent operations."""
        mock_client = MagicMock()
        mock_client.list_tables.return_value = ["table1", "table2"]
        mock_client.has_database.return_value = True

        async_client = AsyncTiDBClient(mock_client)

        # Run different operations concurrently
        tasks = [
            async_client.list_tables(),
            async_client.has_database("test"),
            async_client.current_database(),
        ]

        # Mock current_database after tasks are created
        def current_db_side_effect():
            return "test_db"

        mock_client.current_database.side_effect = current_db_side_effect

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert results[0] == ["table1", "table2"]
        assert results[1] is True
        assert results[2] == "test_db"
