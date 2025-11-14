#!/usr/bin/env python3
"""
Test to verify all async issues have been fixed.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from unittest.mock import Mock, patch, MagicMock
from pytidb.async_client import AsyncTiDBClient
from pytidb.async_table import AsyncTable
from pytidb.async_result import AsyncSQLQueryResult


async def test_async_context_manager():
    """Test that AsyncTiDBClient supports async with."""
    print("Testing async context manager support...")

    try:
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            mock_sync_client = Mock()
            mock_sync_client._db_engine = Mock()
            mock_sync_client._reconnect_params = {}
            mock_sync_client._is_serverless = False
            mock_sync_client.disconnect = Mock()
            mock_connect.return_value = mock_sync_client

            # Connect first, then use as async context manager
            client = await AsyncTiDBClient.connect(
                host="localhost",
                database="test"
            )

            async with client:
                assert isinstance(client, AsyncTiDBClient)
                print("  ✓ Async context manager works!")

            # Verify disconnect was called
            mock_sync_client.disconnect.assert_called()
            print("  ✓ Client was disconnected on exit")

    except Exception as e:
        print(f"✗ Async context manager failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_async_table_result_wrapping():
    """Test that AsyncTable methods return AsyncSQLQueryResult."""
    print("\nTesting AsyncTable result wrapping...")

    try:
        # Mock the sync table
        mock_sync_table = Mock()
        mock_sync_table.name = "users"

        # Create a mock QueryResult that would be returned by sync table
        mock_query_result = Mock()
        mock_sync_table.select = Mock(return_value=mock_query_result)
        mock_sync_table.search = Mock(return_value=mock_query_result)

        # Create async table
        async_table = AsyncTable(mock_sync_table)

        # Test select
        result = await async_table.select()
        # Since we're wrapping, it should be a different object
        assert isinstance(result, AsyncSQLQueryResult)
        print("  ✓ AsyncTable.select() returns AsyncSQLQueryResult!")

        # Test search
        result = await async_table.search("test query")
        assert isinstance(result, AsyncSQLQueryResult)
        print("  ✓ AsyncTable.search() returns AsyncSQLQueryResult!")

        # Verify the sync methods were called
        mock_sync_table.select.assert_called()
        mock_sync_table.search.assert_called()
        print("  ✓ Sync methods were called correctly")

    except Exception as e:
        print(f"✗ AsyncTable result wrapping test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_all_fixes():
    """Run all issue tests."""
    print("=" * 60)
    print("Testing All Async Issues Fixed")
    print("=" * 60)

    issue1_passed = await test_async_context_manager()
    issue2_passed = await test_async_table_result_wrapping()

    print("\n" + "=" * 60)
    if issue1_passed and issue2_passed:
        print("All tests passed! ✓")
        print("\nFixed issues:")
        print("  ✓ [P0] Async context manager support working")
        print("  ✓ [P0] AsyncTable result wrapping correct")
    else:
        print("Some tests failed.")
        if not issue1_passed:
            print("  ✗ [P0] Async context manager support still has issues")
        if not issue2_passed:
            print("  ✗ [P0] AsyncTable result wrapping still has issues")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_all_fixes())
