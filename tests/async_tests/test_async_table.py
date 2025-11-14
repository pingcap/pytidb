"""
Test cases for AsyncTable implementation.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from pytidb.async_table import AsyncTable
from pytidb.table import Table
from pytidb.result import QueryResult, SQLModelQueryResult
from pytidb.schema import TableModel
from sqlmodel import Field, SQLModel


class User(TableModel, table=True):
    """Test model for User table."""
    __tablename__ = "users"

    id: int = Field(primary_key=True)
    name: str
    age: int
    email: str


class TestAsyncTable:
    """Test cases for AsyncTable."""

    @pytest.fixture
    def mock_sync_table(self):
        """Create a mock Table for testing."""
        table = Mock(spec=Table)
        table.name = "users"
        table.model = User
        return table

    @pytest.fixture
    def async_table(self, mock_sync_table):
        """Create an AsyncTable with mocked sync table."""
        return AsyncTable(mock_sync_table)

    @pytest.mark.asyncio
    async def test_async_insert_single(self, async_table, mock_sync_table):
        """Test async insert of single record."""
        user_data = {"name": "John Doe", "age": 25, "email": "john@example.com"}
        mock_result = Mock(spec=User)
        mock_result.id = 1
        mock_result.name = "John Doe"
        mock_result.age = 25
        mock_result.email = "john@example.com"
        mock_sync_table.insert.return_value = mock_result

        result = await async_table.insert(user_data)

        assert result == mock_result
        mock_sync_table.insert.assert_called_once_with(user_data)

    @pytest.mark.asyncio
    async def test_async_insert_model_instance(self, async_table, mock_sync_table):
        """Test async insert of model instance."""
        user = User(name="Jane Doe", age=30, email="jane@example.com")
        mock_result = Mock(spec=User)
        mock_sync_table.insert.return_value = mock_result

        result = await async_table.insert(user)

        assert result == mock_result
        mock_sync_table.insert.assert_called_once_with(user)

    @pytest.mark.asyncio
    async def test_async_select_all(self, async_table, mock_sync_table):
        """Test async select all records."""
        mock_result = Mock(spec=QueryResult)
        mock_sync_table.select.return_value = mock_result

        result = await async_table.select()

        assert result == mock_result
        mock_sync_table.select.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_async_select_with_filters(self, async_table, mock_sync_table):
        """Test async select with filters."""
        mock_result = Mock(spec=QueryResult)
        filters = {"age": {"$gt": 18}}
        mock_sync_table.select.return_value = mock_result

        result = await async_table.select(filters=filters)

        assert result == mock_result
        mock_sync_table.select.assert_called_once_with(filters=filters)

    @pytest.mark.asyncio
    async def test_async_select_with_limit(self, async_table, mock_sync_table):
        """Test async select with limit."""
        mock_result = Mock(spec=QueryResult)
        mock_sync_table.select.return_value = mock_result

        result = await async_table.select(limit=10)

        assert result == mock_result
        mock_sync_table.select.assert_called_once_with(limit=10)

    @pytest.mark.asyncio
    async def test_async_update(self, async_table, mock_sync_table):
        """Test async update operation."""
        mock_result = Mock()
        updates = {"status": "active"}
        filters = {"age": {"$gt": 18}}
        mock_sync_table.update.return_value = mock_result

        result = await async_table.update(updates, filters=filters)

        assert result == mock_result
        mock_sync_table.update.assert_called_once_with(updates, filters=filters)

    @pytest.mark.asyncio
    async def test_async_delete(self, async_table, mock_sync_table):
        """Test async delete operation."""
        mock_result = Mock()
        filters = {"status": "inactive"}
        mock_sync_table.delete.return_value = mock_result

        result = await async_table.delete(filters=filters)

        assert result == mock_result
        mock_sync_table.delete.assert_called_once_with(filters=filters)

    @pytest.mark.asyncio
    async def test_async_search(self, async_table, mock_sync_table):
        """Test async search operation."""
        mock_result = Mock(spec=QueryResult)
        query = "find active users"
        mock_sync_table.search.return_value = mock_result

        result = await async_table.search(query)

        assert result == mock_result
        mock_sync_table.search.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_async_search_with_filters(self, async_table, mock_sync_table):
        """Test async search with filters."""
        mock_result = Mock(spec=QueryResult)
        query = "find users"
        filters = {"age": {"$gt": 18}}
        mock_sync_table.search.return_value = mock_result

        result = await async_table.search(query, filters=filters)

        assert result == mock_result
        mock_sync_table.search.assert_called_once_with(query, filters=filters)

    @pytest.mark.asyncio
    async def test_concurrent_table_operations(self, async_table, mock_sync_table):
        """Test concurrent async table operations."""
        # Mock different results for different operations
        mock_insert_result = Mock(spec=User)
        mock_select_result = Mock(spec=QueryResult)
        mock_update_result = Mock()

        mock_sync_table.insert.return_value = mock_insert_result
        mock_sync_table.select.return_value = mock_select_result
        mock_sync_table.update.return_value = mock_update_result

        # Run operations concurrently
        tasks = [
            async_table.insert({"name": "User1", "age": 25}),
            async_table.select(filters={"age": {"$gt": 18}}),
            async_table.update({"status": "active"}, filters={"age": {"$gt": 18}})
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert mock_sync_table.insert.call_count == 1
        assert mock_sync_table.select.call_count == 1
        assert mock_sync_table.update.call_count == 1

    @pytest.mark.asyncio
    async def test_async_bulk_operations(self, async_table, mock_sync_table):
        """Test async bulk operations."""
        mock_results = [Mock(spec=User) for _ in range(3)]

        # Test bulk insert
        bulk_data = [
            {"name": "User1", "age": 20},
            {"name": "User2", "age": 25},
            {"name": "User3", "age": 30}
        ]

        # For bulk operations, we'll simulate individual inserts
        mock_sync_table.insert.side_effect = mock_results

        tasks = [async_table.insert(data) for data in bulk_data]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert mock_sync_table.insert.call_count == 3

    @pytest.mark.asyncio
    async def test_error_handling_in_table_operations(self, async_table, mock_sync_table):
        """Test error handling in async table operations."""
        from pytidb.errors import TiDBError

        mock_sync_table.insert.side_effect = TiDBError("Insert failed")

        with pytest.raises(TiDBError, match="Insert failed"):
            await async_table.insert({"name": "Invalid User"})

    @pytest.mark.asyncio
    async def test_async_table_method_docstrings(self, async_table):
        """Test that async table methods have proper docstrings."""
        methods_with_docstrings = [
            async_table.insert,
            async_table.select,
            async_table.update,
            async_table.delete,
            async_table.search,
        ]

        for method in methods_with_docstrings:
            assert method.__doc__ is not None, f"Method {method.__name__} missing docstring"
            assert "async" in method.__doc__.lower(), f"Method {method.__name__} docstring should mention async behavior"

    @pytest.mark.asyncio
    async def test_async_table_with_complex_filters(self, async_table, mock_sync_table):
        """Test async table operations with complex filters."""
        mock_result = Mock(spec=QueryResult)

        # Complex filter with multiple conditions
        complex_filters = {
            "$and": [
                {"age": {"$gte": 18}},
                {"age": {"$lte": 65}},
                {"status": "active"}
            ]
        }
        mock_sync_table.select.return_value = mock_result

        result = await async_table.select(filters=complex_filters)

        assert result == mock_result
        mock_sync_table.select.assert_called_once_with(filters=complex_filters)

    @pytest.mark.asyncio
    async def test_async_table_with_ordering(self, async_table, mock_sync_table):
        """Test async table operations with ordering."""
        mock_result = Mock(spec=QueryResult)
        mock_sync_table.select.return_value = mock_result

        result = await async_table.select(order_by=["age DESC", "name ASC"])

        assert result == mock_result
        mock_sync_table.select.assert_called_once_with(order_by=["age DESC", "name ASC"])