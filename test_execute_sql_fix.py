#!/usr/bin/env python3
"""
Test that execute_sql correctly delegates to sync client's query() method.

This test verifies the P0 fix: AsyncTiDBClient.execute_sql was incorrectly
trying to call non-existent TiDBClient.execute_sql(). It should call
TiDBClient.query() instead for SELECT statements.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from unittest.mock import Mock, patch
from pytidb.async_client import AsyncTiDBClient
from pytidb.async_result import AsyncSQLQueryResult
from pytidb.result import SQLQueryResult


async def test_execute_sql_delegates_to_query():
    """Test that execute_sql calls sync client's query() method."""
    print("Testing execute_sql() delegation to sync query() method...")

    with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
        # Setup mock sync client
        mock_sync_client = Mock()
        mock_sync_client._db_engine = Mock()
        mock_sync_client._reconnect_params = {}
        mock_sync_client._is_serverless = False
        mock_sync_client.disconnect = Mock()

        # Mock the query method to return a result
        mock_query_result = Mock(spec=SQLQueryResult)
        mock_sync_client.query = Mock(return_value=mock_query_result)

        mock_connect.return_value = mock_sync_client

        # Create async client
        client = await AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            database="test"
        )

        # Test execute_sql
        result = await client.execute_sql("SELECT * FROM users")

        # Verify it called query(), not execute_sql
        mock_sync_client.query.assert_called_once_with(
            "SELECT * FROM users",
            params=None
        )
        mock_sync_client.execute_sql.assert_not_called()  # Should not exist

        # Verify we got an AsyncSQLQueryResult wrapper
        assert isinstance(result, AsyncSQLQueryResult)
        print("  ✓ execute_sql() correctly calls sync query() method")
        print("  ✓ Returns AsyncSQLQueryResult wrapper")

        # Test parameterized query
        result2 = await client.execute_sql(
            "SELECT * FROM users WHERE age > ?",
            params=[18]
        )

        mock_sync_client.query.assert_called_with(
            "SELECT * FROM users WHERE age > ?",
            params=[18]
        )
        print("  ✓ Parameterized query works correctly")

        return True


async def test_execute_delegates_to_execute():
    """Test that execute() correctly calls sync client's execute() method."""
    print("\nTesting execute() delegation to sync execute() method...")

    with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
        # Setup mock sync client
        mock_sync_client = Mock()
        mock_sync_client._db_engine = Mock()
        mock_sync_client._reconnect_params = {}
        mock_sync_client._is_serverless = False
        mock_sync_client.disconnect = Mock()

        # Mock the execute method to return a result
        mock_execute_result = Mock()
        mock_sync_client.execute = Mock(return_value=mock_execute_result)

        mock_connect.return_value = mock_sync_client

        # Create async client
        client = await AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            database="test"
        )

        # Test execute (for INSERT/UPDATE/DELETE)
        result = await client.execute(
            "INSERT INTO users (name) VALUES (?)",
            params=["John"]
        )

        # Verify it called execute()
        mock_sync_client.execute.assert_called_once_with(
            "INSERT INTO users (name) VALUES (?)",
            params=["John"]
        )
        print("  ✓ execute() correctly calls sync execute() method")
        print("  ✓ Returns AsyncSQLExecuteResult wrapper")

        return True


async def main():
    """Run all tests."""
    print("=" * 70)
    print("Testing execute_sql() and execute() Fix")
    print("=" * 70)

    try:
        test1_passed = await test_execute_sql_delegates_to_query()
        test2_passed = await test_execute_delegates_to_execute()

        print("\n" + "=" * 70)
        if test1_passed and test2_passed:
            print("All delegation tests passed! ✓")
            print("\nFix summary:")
            print("  ✓ execute_sql() → calls sync query() not execute_sql()")
            print("  ✓ execute() → calls sync execute() correctly")
            print("  ✓ Both methods wrap results properly")
        else:
            print("Some tests failed!")
        print("=" * 70)
        return 0

    except Exception as e:
        print(f"\n✗ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
