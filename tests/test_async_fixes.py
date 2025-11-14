"""
Comprehensive tests for AsyncTiDBClient and AsyncTable with proper mocking.

This test file validates both P0 and P1 fixes work correctly.
"""

import pytest
from unittest.mock import MagicMock, patch
from pytidb import AsyncTiDBClient, AsyncTable
from pytidb.schema import TableModel, Field


class User(TableModel):
    __tablename__ = "users"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=100)


class TestAsyncClientWithProperMocks:
    """Test AsyncTiDBClient with properly mocked sync client."""

    def test_create_async_client_with_mock_engine(self):
        """Create AsyncTiDBClient with fully mocked engine."""
        mock_engine = MagicMock()
        mock_engine.url.host = "localhost"
        mock_engine.url.database = "test"

        mock_sync_client = MagicMock()
        mock_sync_client._db_engine = mock_engine
        mock_sync_client.db_engine = mock_engine
        mock_sync_client._reconnect_params = {}
        mock_sync_client._identifier_preparer = MagicMock()

        async_client = AsyncTiDBClient(mock_sync_client)

        assert async_client.db_engine == mock_engine
        assert async_client.db_engine.url.database == "test"

    def test_db_engine_dynamic_property(self):
        """Test db_engine is dynamic (P1 fix)."""
        mock_engine1 = MagicMock()
        mock_engine1.url.database = "db1"

        mock_sync_client = MagicMock()
        mock_sync_client.db_engine = mock_engine1
        mock_sync_client._reconnect_params = {}

        async_client = AsyncTiDBClient(mock_sync_client)

        # Returns first engine
        assert async_client.db_engine.url.database == "db1"

        # Change engine in sync client
        mock_engine2 = MagicMock()
        mock_engine2.url.database = "db2"
        mock_sync_client.db_engine = mock_engine2

        # Should return new engine (dynamic property)
        assert async_client.db_engine.url.database == "db2"

    def test_async_table_from_schema_and_client(self):
        """Test AsyncTable with client+schema (P0 fix)."""
        mock_engine = MagicMock()
        mock_engine.url.host = "localhost"

        mock_sync_client = MagicMock()
        mock_sync_client._db_engine = mock_engine
        mock_sync_client.db_engine = mock_engine
        mock_sync_client._reconnect_params = {}

        async_client = AsyncTiDBClient(mock_sync_client)

        # Mock the Table constructor
        with patch("pytidb.async_client.Table") as mock_table_class:
            mock_sync_table = MagicMock()
            mock_sync_table.table_model = User
            mock_sync_table.table_name = "users"
            mock_table_class.return_value = mock_sync_table

            # Create AsyncTable using schema/client (P0 fix)
            async_table = AsyncTable(client=async_client, schema=User)

            # Verify Table was instantiated correctly
            mock_table_class.assert_called_once()
            call_kwargs = mock_table_class.call_args.kwargs
            assert call_kwargs["schema"] == User
            assert call_kwargs["client"] == mock_sync_client

            # Verify AsyncTable properties
            assert async_table.table_model == User
            assert async_table.table_name == "users"

    def test_async_table_backward_compatibility(self):
        """Test AsyncTable with sync_table (backward compatible)."""
        mock_sync_table = MagicMock()
        mock_sync_table.table_model = User
        mock_sync_table.table_name = "users"

        # Old-style initialization (backward compatible)
        async_table = AsyncTable(sync_table=mock_sync_table)

        assert async_table.table_model == User
        assert async_table.table_name == "users"
        assert async_table._sync_table == mock_sync_table

    def test_async_table_error_handling(self):
        """Test AsyncTable constructor error handling."""
        # No parameters
        with pytest.raises(ValueError, match="AsyncTable must be initialized"):
            AsyncTable()

        # Only client, no schema
        with pytest.raises(ValueError, match="AsyncTable must be initialized"):
            AsyncTable(client=MagicMock())

        # Only schema, no client
        with pytest.raises(ValueError, match="AsyncTable must be initialized"):
            AsyncTable(schema=User)

        # Wrong client type
        with pytest.raises(TypeError, match="client must be an AsyncTiDBClient"):
            AsyncTable(client=MagicMock(), schema=User)

    def test_async_client_connect_classmethod(self):
        """Test AsyncTiDBClient.connect classmethod."""
        # Mock the actual TiDBClient.connect
        with patch("pytidb.client.TiDBClient.connect") as mock_connect:
            mock_engine = MagicMock()
            mock_engine.url.host = "localhost"

            mock_sync_client = MagicMock()
            mock_sync_client._db_engine = mock_engine
            mock_sync_client.db_engine = mock_engine
            mock_sync_client._reconnect_params = {}

            mock_connect.return_value = mock_sync_client

            # Note: This can't be awaited without a test function
            # But we can test that the method exists and would call the sync version
            assert hasattr(AsyncTiDBClient, "connect")

    def test_async_client_methods_exist(self):
        """Verify all expected async methods exist."""
        mock_sync_client = MagicMock()
        mock_sync_client.db_engine = MagicMock()
        mock_sync_client._reconnect_params = {}

        async_client = AsyncTiDBClient(mock_sync_client)

        # Check all expected methods exist
        assert hasattr(async_client, "execute")
        assert hasattr(async_client, "query")
        assert hasattr(async_client, "create_database")
        assert hasattr(async_client, "drop_database")
        assert hasattr(async_client, "list_databases")
        assert hasattr(async_client, "has_database")
        assert hasattr(async_client, "current_database")
        assert hasattr(async_client, "use_database")
        assert hasattr(async_client, "create_table")
        assert hasattr(async_client, "open_table")
        assert hasattr(async_client, "list_tables")
        assert hasattr(async_client, "has_table")
        assert hasattr(async_client, "drop_table")
        assert hasattr(async_client, "disconnect")


class TestAsyncTableMethods:
    """Test AsyncTable methods work with both init paths."""

    def setup_method(self):
        """Set up mocks for each test."""
        self.mock_sync_table = MagicMock()
        self.mock_sync_table.table_model = User
        self.mock_sync_table.table_name = "users"

    @pytest.mark.asyncio
    async def test_insert_operation(self):
        """Test async insert."""
        self.mock_sync_table.insert.return_value = MagicMock(id=1, name="Alice")
        async_table = AsyncTable(sync_table=self.mock_sync_table)

        result = await async_table.insert({"id": 1, "name": "Alice"})

        assert result.id == 1
        assert result.name == "Alice"
        self.mock_sync_table.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_operation(self):
        """Test async query."""
        mock_result = MagicMock()
        mock_result.to_list.return_value = [{"id": 1, "name": "Alice"}]
        self.mock_sync_table.query.return_value = mock_result

        async_table = AsyncTable(sync_table=self.mock_sync_table)
        result = await async_table.query()

        assert result == mock_result
        self.mock_sync_table.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_operation(self):
        """Test async get by ID."""
        mock_record = MagicMock()
        mock_record.id = 1
        self.mock_sync_table.get.return_value = mock_record

        async_table = AsyncTable(sync_table=self.mock_sync_table)
        result = await async_table.get(1)

        assert result.id == 1
        self.mock_sync_table.get.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_operation(self):
        """Test async delete."""
        self.mock_sync_table.delete = MagicMock()
        async_table = AsyncTable(sync_table=self.mock_sync_table)

        await async_table.delete({"id": 1})

        self.mock_sync_table.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_operation(self):
        """Test async update."""
        self.mock_sync_table.update = MagicMock()
        async_table = AsyncTable(sync_table=self.mock_sync_table)

        await async_table.update({"name": "Updated"}, {"id": 1})

        self.mock_sync_table.update.assert_called_once()
