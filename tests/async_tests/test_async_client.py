"""
Test cases for AsyncTiDBClient implementation.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import List, Dict, Any

from pytidb.async_client import AsyncTiDBClient
from pytidb.client import TiDBClient
from pytidb.result import SQLQueryResult, SQLExecuteResult


class TestAsyncTiDBClient:
    """Test cases for AsyncTiDBClient."""

    @pytest.fixture
    def mock_sync_client(self):
        """Create a mock TiDBClient for testing."""
        client = Mock(spec=TiDBClient)
        client._db_engine = Mock()
        client._reconnect_params = {}
        client._is_serverless = False
        return client

    @pytest.fixture
    def async_client(self, mock_sync_client):
        """Create an AsyncTiDBClient with mocked sync client."""
        return AsyncTiDBClient(mock_sync_client)

    @pytest.mark.asyncio
    async def test_async_connect(self):
        """Test async connection creation."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            mock_sync_client = Mock(spec=TiDBClient)
            mock_connect.return_value = mock_sync_client

            async_client = await AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            )

            assert isinstance(async_client, AsyncTiDBClient)
            mock_connect.assert_called_once_with(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            )

    @pytest.mark.asyncio
    async def test_async_disconnect(self, async_client, mock_sync_client):
        """Test async disconnection."""
        await async_client.disconnect()
        mock_sync_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_execute_sql(self, async_client, mock_sync_client):
        """Test async SQL execution."""
        mock_result = Mock(spec=SQLQueryResult)
        mock_sync_client.query = Mock(return_value=mock_result)

        result = await async_client.execute_sql("SELECT * FROM users")

        assert result is not None
        mock_sync_client.query.assert_called_once_with("SELECT * FROM users", params=None)

    @pytest.mark.asyncio
    async def test_async_execute_sql_with_params(self, async_client, mock_sync_client):
        """Test async SQL execution with parameters."""
        mock_result = Mock(spec=SQLQueryResult)
        mock_sync_client.query = Mock(return_value=mock_result)

        result = await async_client.execute_sql(
            "SELECT * FROM users WHERE age > ?",
            params=[18]
        )

        assert result is not None
        mock_sync_client.query.assert_called_once_with(
            "SELECT * FROM users WHERE age > ?",
            params=[18]
        )

    @pytest.mark.asyncio
    async def test_async_get_table(self, async_client, mock_sync_client):
        """Test async table retrieval."""
        mock_table = Mock()
        mock_sync_client.get_table.return_value = mock_table

        table = await async_client.get_table("users")

        assert table is not None
        mock_sync_client.get_table.assert_called_once_with("users")

    @pytest.mark.asyncio
    async def test_async_use_database(self, async_client, mock_sync_client):
        """Test async database switching."""
        await async_client.use_database("new_database")
        mock_sync_client.use_database.assert_called_once_with("new_database")

    @pytest.mark.asyncio
    async def test_async_execute(self, async_client, mock_sync_client):
        """Test async execute method."""
        mock_result = Mock(spec=SQLExecuteResult)
        mock_sync_client.execute.return_value = mock_result

        result = await async_client.execute("INSERT INTO users (name) VALUES ('John')")

        assert result == mock_result
        mock_sync_client.execute.assert_called_once_with("INSERT INTO users (name) VALUES ('John')")

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, async_client, mock_sync_client):
        """Test concurrent async operations."""
        mock_sync_client.execute_sql.side_effect = [
            Mock(spec=SQLQueryResult),
            Mock(spec=SQLQueryResult),
            Mock(spec=SQLQueryResult)
        ]

        # Run multiple queries concurrently
        tasks = [
            async_client.execute_sql("SELECT * FROM users"),
            async_client.execute_sql("SELECT * FROM products"),
            async_client.execute_sql("SELECT * FROM orders")
        ]

        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        assert mock_sync_client.execute_sql.call_count == 3

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test async context manager functionality."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            mock_sync_client = Mock(spec=TiDBClient)
            mock_connect.return_value = mock_sync_client

            async with AsyncTiDBClient.connect(
                host="localhost",
                database="test"
            ) as client:
                assert isinstance(client, AsyncTiDBClient)
                # Context manager should work without explicit disconnect

            # Note: disconnect is not automatically called in context manager exit
            # This is intentional to match the sync API behavior

    @pytest.mark.asyncio
    async def test_error_handling(self, async_client, mock_sync_client):
        """Test error handling in async context."""
        from pytidb.errors import TiDBError

        mock_sync_client.execute_sql.side_effect = TiDBError("Database error")

        with pytest.raises(TiDBError, match="Database error"):
            await async_client.execute_sql("INVALID SQL")

    @pytest.mark.asyncio
    async def test_transaction_rollback(self, async_client, mock_sync_client):
        """Test transaction rollback in async context."""
        from pytidb.errors import TiDBError

        # Simulate failed transaction
        mock_sync_client.execute.side_effect = [
            Mock(spec=SQLExecuteResult),  # First call succeeds
            TiDBError("Transaction failed")  # Second call fails
        ]

        with pytest.raises(TiDBError, match="Transaction failed"):
            await async_client.execute("UPDATE users SET balance = balance - 100")

        # Verify the call was made despite the error
        mock_sync_client.execute.assert_called()

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self):
        """Test connection timeout in async context."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            from pytidb.errors import ConnectionError

            mock_connect.side_effect = ConnectionError("Connection timeout")

            with pytest.raises(ConnectionError, match="Connection timeout"):
                await AsyncTiDBClient.connect(
                    host="unreachable-host",
                    port=4000,
                    timeout=1
                )

    @pytest.mark.asyncio
    async def test_async_method_docstrings(self, async_client):
        """Test that async methods have proper docstrings."""
        # Check that async methods have docstrings
        methods_with_docstrings = [
            async_client.connect,
            async_client.disconnect,
            async_client.execute_sql,
            async_client.execute,
            async_client.get_table,
            async_client.use_database,
        ]

        for method in methods_with_docstrings:
            assert method.__doc__ is not None, f"Method {method.__name__} missing docstring"
            assert "async" in method.__doc__.lower(), f"Method {method.__name__} docstring should mention async behavior"