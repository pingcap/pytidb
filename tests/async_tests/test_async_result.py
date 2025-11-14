"""
Test cases for AsyncResult implementation.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from pytidb.async_result import AsyncQueryResult, AsyncSQLQueryResult
from pytidb.result import SQLQueryResult, QueryResult
from sqlalchemy import Result


class TestAsyncQueryResult:
    """Test cases for AsyncQueryResult."""

    @pytest.fixture
    def mock_sync_result(self):
        """Create a mock SQLQueryResult for testing."""
        result = Mock(spec=SQLQueryResult)
        result.scalar.return_value = 42
        result.one.return_value = {"id": 1, "name": "John"}
        result.fetchall.return_value = [
            (1, "John", 25),
            (2, "Jane", 30)
        ]
        result.keys.return_value = ["id", "name", "age"]
        result.to_list.return_value = [
            {"id": 1, "name": "John", "age": 25},
            {"id": 2, "name": "Jane", "age": 30}
        ]
        return result

    @pytest.fixture
    def async_result(self, mock_sync_result):
        """Create an AsyncSQLQueryResult with mocked sync result."""
        return AsyncSQLQueryResult(mock_sync_result)

    @pytest.mark.asyncio
    async def test_async_scalar(self, async_result, mock_sync_result):
        """Test async scalar result."""
        result = await async_result.scalar()

        assert result == 42
        mock_sync_result.scalar.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_one(self, async_result, mock_sync_result):
        """Test async one result."""
        result = await async_result.one()

        assert result == {"id": 1, "name": "John"}
        mock_sync_result.one.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_fetchall(self, async_result, mock_sync_result):
        """Test async fetchall."""
        result = await async_result.fetchall()

        expected = [
            (1, "John", 25),
            (2, "Jane", 30)
        ]
        assert result == expected
        mock_sync_result.fetchall.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_to_list(self, async_result, mock_sync_result):
        """Test async conversion to list."""
        result = await async_result.to_list()

        expected = [
            {"id": 1, "name": "John", "age": 25},
            {"id": 2, "name": "Jane", "age": 30}
        ]
        assert result == expected
        mock_sync_result.to_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_to_pandas(self, async_result, mock_sync_result):
        """Test async conversion to pandas."""
        mock_df = Mock()
        mock_sync_result.to_pandas.return_value = mock_df

        result = await async_result.to_pandas()

        assert result == mock_df
        mock_sync_result.to_pandas.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_keys(self, async_result, mock_sync_result):
        """Test async keys retrieval."""
        result = await async_result.keys()

        expected = ["id", "name", "age"]
        assert result == expected
        mock_sync_result.keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_concurrent_result_operations(self, async_result, mock_sync_result):
        """Test concurrent async result operations."""
        # Run multiple operations concurrently
        tasks = [
            async_result.scalar(),
            async_result.one(),
            async_result.to_list()
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert results[0] == 42
        assert results[1] == {"id": 1, "name": "John"}
        assert results[2] == [
            {"id": 1, "name": "John", "age": 25},
            {"id": 2, "name": "Jane", "age": 30}
        ]

        # Verify all methods were called
        mock_sync_result.scalar.assert_called_once()
        mock_sync_result.one.assert_called_once()
        mock_sync_result.to_list.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_result_operations(self, async_result, mock_sync_result):
        """Test error handling in async result operations."""
        from pytidb.errors import TiDBError

        mock_sync_result.scalar.side_effect = TiDBError("Database error")

        with pytest.raises(TiDBError, match="Database error"):
            await async_result.scalar()

    @pytest.mark.asyncio
    async def test_async_result_method_docstrings(self, async_result):
        """Test that async result methods have proper docstrings."""
        methods_with_docstrings = [
            async_result.scalar,
            async_result.one,
            async_result.fetchall,
            async_result.to_list,
            async_result.to_pandas,
            async_result.keys,
        ]

        for method in methods_with_docstrings:
            assert method.__doc__ is not None, f"Method {method.__name__} missing docstring"
            assert "async" in method.__doc__.lower(), f"Method {method.__name__} docstring should mention async behavior"

    @pytest.mark.asyncio
    async def test_async_result_with_no_results(self, async_result, mock_sync_result):
        """Test async result operations with empty results."""
        mock_sync_result.scalar.return_value = None
        mock_sync_result.one.side_effect = Exception("No result found")
        mock_sync_result.fetchall.return_value = []
        mock_sync_result.to_list.return_value = []

        # Test scalar with no results
        scalar_result = await async_result.scalar()
        assert scalar_result is None

        # Test one with no results
        with pytest.raises(Exception, match="No result found"):
            await async_result.one()

        # Test fetchall with no results
        fetchall_result = await async_result.fetchall()
        assert fetchall_result == []

        # Test to_list with no results
        list_result = await async_result.to_list()
        assert list_result == []

    @pytest.mark.asyncio
    async def test_async_result_with_large_dataset(self, async_result, mock_sync_result):
        """Test async result operations with large dataset."""
        # Create large dataset
        large_data = [
            (i, f"User{i}", 20 + (i % 50))
            for i in range(1000)
        ]
        large_list = [
            {"id": i, "name": f"User{i}", "age": 20 + (i % 50)}
            for i in range(1000)
        ]

        mock_sync_result.fetchall.return_value = large_data
        mock_sync_result.to_list.return_value = large_list

        # Test fetchall with large dataset
        fetchall_result = await async_result.fetchall()
        assert len(fetchall_result) == 1000
        assert fetchall_result[0] == (0, "User0", 20)
        assert fetchall_result[-1] == (999, "User999", 69)

        # Test to_list with large dataset
        list_result = await async_result.to_list()
        assert len(list_result) == 1000
        assert list_result[0] == {"id": 0, "name": "User0", "age": 20}
        assert list_result[-1] == {"id": 999, "name": "User999", "age": 69}


# Import asyncio for the concurrent tests
import asyncio

if __name__ == "__main__":
    pytest.main([__file__])