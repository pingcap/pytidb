"""
Unit tests for AsyncTable constructor with schema/client support (P0 fix).
"""

import pytest
from unittest.mock import MagicMock, patch
from pytidb import AsyncTiDBClient, AsyncTable
from pytidb.schema import TableModel, Field


class TestSchema(TableModel):
    __tablename__ = "test_users"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=100)


class TestAsyncTableConstructor:
    """Test AsyncTable constructor with different initialization paths."""

    def test_async_table_from_sync_table(self):
        """Test AsyncTable(sync_table=...) path (internal wrapping)."""
        mock_sync_table = MagicMock()
        mock_sync_table.table_model = TestSchema
        mock_sync_table.table_name = "test_users"

        async_table = AsyncTable(sync_table=mock_sync_table)

        assert async_table._sync_table == mock_sync_table
        assert async_table.table_model == TestSchema
        assert async_table.table_name == "test_users"

    def test_async_table_from_schema_and_client(self):
        """Test AsyncTable(client=..., schema=...) path (public API)."""
        mock_sync_client = MagicMock()
        mock_async_client = AsyncTiDBClient(mock_sync_client)

        # Mock the Table constructor to avoid database connections
        with patch("pytidb.async_client.Table") as mock_table_class:
            mock_sync_table = MagicMock()
            mock_sync_table.table_model = TestSchema
            mock_sync_table.table_name = "test_users"
            mock_table_class.return_value = mock_sync_table

            # Create AsyncTable from schema and client
            async_table = AsyncTable(client=mock_async_client, schema=TestSchema)

            # Verify Table was instantiated correctly
            mock_table_class.assert_called_once_with(
                schema=TestSchema,
                client=mock_sync_client
            )

            assert async_table.table_model == TestSchema
            assert async_table.table_name == "test_users"
            assert async_table._sync_table == mock_sync_table

    def test_async_table_requires_either_sync_or_client_schema(self):
        """Test that constructor requires either sync_table or both client and schema."""
        with pytest.raises(ValueError, match="AsyncTable must be initialized"):
            AsyncTable()

        with pytest.raises(ValueError, match="AsyncTable must be initialized"):
            AsyncTable(client=MagicMock())

        with pytest.raises(ValueError, match="AsyncTable must be initialized"):
            AsyncTable(schema=TestSchema)

    def test_async_table_client_must_be_async_client(self):
        """Test that client parameter must be AsyncTiDBClient instance."""
        with pytest.raises(TypeError, match="client must be an AsyncTiDBClient"):
            AsyncTable(client=MagicMock(), schema=TestSchema)

    @pytest.mark.asyncio
    async def test_async_table_operations_with_new_constructor(self):
        """Test that async operations work with the new constructor path."""
        mock_client = MagicMock()
        mock_client.db_engine = MagicMock()
        async_client = AsyncTiDBClient(mock_client)

        # Mock the Table constructor
        with patch("pytidb.async_client.Table") as mock_table_class:
            mock_sync_table = MagicMock()
            mock_sync_table.table_model = TestSchema
            mock_sync_table.table_name = "test_users"
            mock_sync_table.insert = MagicMock(return_value=MagicMock(id=1, name="Alice"))
            mock_table_class.return_value = mock_sync_table

            # Create AsyncTable using schema/client
            async_table = AsyncTable(client=async_client, schema=TestSchema)

            # Test async insert
            result = await async_table.insert({"id": 1, "name": "Alice"})
            assert result.id == 1
            assert result.name == "Alice"

    def test_backward_compatibility_with_sync_table_path(self):
        """Ensure existing code using sync_table parameter still works."""
        mock_sync_table = MagicMock()
        mock_sync_table.table_model = TestSchema
        mock_sync_table.table_name = "test_users"
        mock_sync_table.insert = MagicMock()

        # This is how AsyncTiDBClient.create_table uses it
        async_table = AsyncTable(sync_table=mock_sync_table)

        assert async_table.table_model == TestSchema
        assert async_table.table_name == "test_users"

    @pytest.mark.asyncio
    async def test_async_table_async_methods_still_work(self):
        """Verify all async methods work regardless of constructor path."""
        mock_sync_table = MagicMock()
        mock_sync_table.table_model = TestSchema
        mock_sync_table.table_name = "test_users"
        mock_sync_table.insert = MagicMock(return_value=MagicMock(id=1, name="Test"))

        async_table = AsyncTable(sync_table=mock_sync_table)

        # Test insert
        result = await async_table.insert({"id": 1, "name": "Test"})
        assert result.id == 1
        assert async_table.table_name == "test_users"

    def test_async_table_properties(self):
        """Test that properties are correctly set in both constructor paths."""
        # Path 1: sync_table
        mock_sync_table = MagicMock()
        mock_sync_table.table_model = TestSchema
        mock_sync_table.table_name = "test_table"

        async_table1 = AsyncTable(sync_table=mock_sync_table)
        assert async_table1.table_model == TestSchema
        assert async_table1.table_name == "test_table"

        # Path 2: client + schema
        mock_sync_client = MagicMock()
        mock_async_client = AsyncTiDBClient(mock_sync_client)

        with patch("pytidb.async_client.Table") as mock_table_class:
            mock_sync_table2 = MagicMock()
            mock_sync_table2.table_model = TestSchema
            mock_sync_table2.table_name = "test_users"
            mock_table_class.return_value = mock_sync_table2

            async_table2 = AsyncTable(client=mock_async_client, schema=TestSchema)
            assert async_table2.table_model == TestSchema
            assert async_table2.table_name == "test_users"
