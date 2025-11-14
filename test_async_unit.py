#!/usr/bin/env python3
"""
Unit tests for async PyTiDB implementation.

These tests verify the async wrapper functionality without requiring
a real database connection.
"""
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

try:
    from pytidb.async_result import AsyncSQLQueryResult
    from pytidb.async_table import AsyncTable
    from pytidb.async_client import AsyncTiDBClient
    from pytidb.result import SQLQueryResult
    from pytidb.client import TiDBClient
    from pytidb.table import Table
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the pytidb directory")
    sys.exit(1)


class TestAsyncResult:
    """Test AsyncSQLQueryResult functionality."""

    @staticmethod
    async def test_async_scalar():
        """Test async scalar method."""
        # Create mock sync result
        mock_sync_result = Mock(spec=SQLQueryResult)
        mock_sync_result.scalar.return_value = 42

        # Create async result wrapper
        async_result = AsyncSQLQueryResult(mock_sync_result)

        # Test async scalar
        result = await async_result.scalar()
        assert result == 42
        mock_sync_result.scalar.assert_called_once()
        print("✓ test_async_scalar passed")

    @staticmethod
    async def test_async_to_list():
        """Test async to_list method."""
        # Create mock sync result
        mock_sync_result = Mock(spec=SQLQueryResult)
        mock_data = [
            {"id": 1, "name": "John", "age": 25},
            {"id": 2, "name": "Jane", "age": 30}
        ]
        mock_sync_result.to_list.return_value = mock_data

        # Create async result wrapper
        async_result = AsyncSQLQueryResult(mock_sync_result)

        # Test async to_list
        result = await async_result.to_list()
        assert result == mock_data
        mock_sync_result.to_list.assert_called_once()
        print("✓ test_async_to_list passed")

    @staticmethod
    async def test_concurrent_operations():
        """Test concurrent async operations."""
        # Create mock sync result
        mock_sync_result = Mock(spec=SQLQueryResult)
        mock_sync_result.scalar.return_value = 42
        mock_sync_result.to_list.return_value = [{"id": 1, "name": "John"}]

        # Create async result wrapper
        async_result = AsyncSQLQueryResult(mock_sync_result)

        # Run operations concurrently
        tasks = [
            async_result.scalar(),
            async_result.to_list()
        ]
        results = await asyncio.gather(*tasks)

        assert results[0] == 42
        assert results[1] == [{"id": 1, "name": "John"}]
        print("✓ test_concurrent_operations passed")


class TestAsyncTable:
    """Test AsyncTable functionality."""

    @staticmethod
    async def test_async_insert():
        """Test async insert operation."""
        # Create mock sync table
        mock_sync_table = Mock(spec=Table)
        mock_sync_table.name = "users"
        mock_sync_table.insert.return_value = {"id": 1, "name": "John"}

        # Create async table wrapper
        async_table = AsyncTable(mock_sync_table)

        # Test async insert
        data = {"name": "John", "age": 25}
        result = await async_table.insert(data)
        assert result == {"id": 1, "name": "John"}
        mock_sync_table.insert.assert_called_once_with(data)
        print("✓ test_async_insert passed")

    @staticmethod
    async def test_async_select():
        """Test async select operation."""
        # Create mock sync table
        mock_sync_table = Mock()
        mock_sync_table.name = "users"
        mock_result = Mock()
        mock_sync_table.select = Mock(return_value=mock_result)

        # Create async table wrapper
        async_table = AsyncTable(mock_sync_table)

        # Test async select - should return AsyncSQLQueryResult wrapper
        result = await async_table.select(filters={"age": {"$gt": 18}})
        from pytidb.async_result import AsyncSQLQueryResult
        assert isinstance(result, AsyncSQLQueryResult)
        mock_sync_table.select.assert_called_once_with(
            filters={"age": {"$gt": 18}},
            limit=None,
            order_by=None
        )
        print("✓ test_async_select passed")


class TestAsyncClient:
    """Test AsyncTiDBClient functionality."""

    @staticmethod
    async def test_async_connect():
        """Test async connection."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Create mock sync client
            mock_sync_client = Mock(spec=TiDBClient)
            mock_sync_client._db_engine = Mock()
            mock_sync_client._reconnect_params = {}
            mock_sync_client._is_serverless = False
            mock_connect.return_value = mock_sync_client

            # Test async connect
            async_client = await AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                database="test"
            )

            assert isinstance(async_client, AsyncTiDBClient)
            mock_connect.assert_called_once()
            print("✓ test_async_connect passed")

    @staticmethod
    async def test_async_execute_sql():
        """Test async SQL execution."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Create mock sync client and result
            mock_sync_client = Mock()
            mock_sync_client._db_engine = Mock()
            mock_sync_client._reconnect_params = {}
            mock_sync_client._is_serverless = False
            mock_sync_client.query = Mock()  # Use query, not execute_sql

            mock_result = Mock(spec=SQLQueryResult)
            mock_sync_client.query.return_value = mock_result
            mock_connect.return_value = mock_sync_client

            # Create async client
            async_client = await AsyncTiDBClient.connect()

            # Test async SQL execution
            result = await async_client.execute_sql("SELECT * FROM users")
            assert result is not None
            mock_sync_client.query.assert_called_once_with("SELECT * FROM users", params=None)
            mock_sync_client.execute_sql.assert_not_called()  # Should not exist
            print("✓ test_async_execute_sql passed")

    @staticmethod
    async def test_async_get_table():
        """Test async table retrieval."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Create mock sync client and table
            mock_sync_client = Mock()
            mock_sync_client._db_engine = Mock()
            mock_sync_client._reconnect_params = {}
            mock_sync_client._is_serverless = False
            mock_sync_client.open_table = Mock()

            mock_table = Mock(spec=Table)
            mock_sync_client.open_table.return_value = mock_table
            mock_connect.return_value = mock_sync_client

            # Create async client
            async_client = await AsyncTiDBClient.connect()

            # Test async table retrieval
            table = await async_client.get_table("users")
            assert table is not None
            mock_sync_client.open_table.assert_called_once_with("users")
            print("✓ test_async_get_table passed")


async def run_all_tests():
    """Run all unit tests."""
    print("Running Async PyTiDB Unit Tests...")
    print("=" * 50)

    # Test AsyncResult
    await TestAsyncResult.test_async_scalar()
    await TestAsyncResult.test_async_to_list()
    await TestAsyncResult.test_concurrent_operations()

    # Test AsyncTable
    await TestAsyncTable.test_async_insert()
    await TestAsyncTable.test_async_select()

    # Test AsyncClient
    await TestAsyncClient.test_async_connect()
    await TestAsyncClient.test_async_execute_sql()
    await TestAsyncClient.test_async_get_table()

    print("=" * 50)
    print("All unit tests passed! ✓")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
    print("\nTesting imports...")
    try:
        from pytidb import AsyncTiDBClient, AsyncTable, AsyncSQLQueryResult
        print("✓ All async imports successful")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        sys.exit(1)

    print("\nAsync PyTiDB implementation is ready for testing!")
    print("\nExample usage:")
    print("""
import asyncio
from pytidb import AsyncTiDBClient

async def main():
    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        database="test_db"
    ) as client:
        # Get table
        table = await client.get_table("users")

        # Insert data
        await table.insert({"name": "John", "age": 25})

        # Query data
        result = await table.select(filters={"age": {"$gt": 18}})
        users = await result.to_list()
        print(f"Found {len(users)} users")

if __name__ == "__main__":
    asyncio.run(main())
""")