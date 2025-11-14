#!/usr/bin/env python3
"""
Test that AsyncTiDBClient.connect() works directly with async with.
This verifies the new _ConnectContext helper class works correctly.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from unittest.mock import Mock, patch
from pytidb.async_client import AsyncTiDBClient


async def test_connect_async_context_manager():
    """Test AsyncTiDBClient.connect() can be used directly with async with."""
    print("Testing: async with AsyncTiDBClient.connect(...)")

    with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
        # Setup mock sync client
        mock_sync_client = Mock()
        mock_sync_client._db_engine = Mock()
        mock_sync_client._reconnect_params = {}
        mock_sync_client._is_serverless = False
        mock_sync_client.disconnect = Mock()
        mock_sync_client.query = Mock()

        mock_connect.return_value = mock_sync_client

        # Test 1: Using async with directly on connect()
        print("\n  Test 1: Using connect() directly in async with...")
        async with AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            database="test_db"
        ) as client:
            assert isinstance(client, AsyncTiDBClient)
            # Test that we can use the client
            await client.execute_sql("SELECT * FROM users")
            mock_sync_client.query.assert_called_with("SELECT * FROM users", params=None)

        # Verify disconnect was called automatically
        assert mock_sync_client.disconnect.call_count == 1
        print("  ✓ Client automatically disconnected on exit")

        # Test 2: Using await with connect() (traditional pattern)
        print("\n  Test 2: Using await with connect() (traditional)...")
        client = await AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            database="test_db"
        )
        assert isinstance(client, AsyncTiDBClient)

        async with client:
            await client.execute_sql("SELECT * FROM users")

        # Verify disconnect was called (this time manually via async with client)
        mock_sync_client.disconnect.assert_called()
        print("  ✓ Traditional await pattern still works")

        # Test 3: Manual disconnect (manual pattern)
        print("\n  Test 3: Using manual disconnect pattern...")
        client = await AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            database="test_db"
        )
        try:
            await client.execute_sql("SELECT * FROM users")
        finally:
            await client.disconnect()

        print("  ✓ Manual disconnect pattern still works")

        print("\n✓ All connect() usage patterns work correctly!")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("Testing AsyncTiDBClient.connect() Context Manager Support")
    print("=" * 70)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_connect_async_context_manager())
        print("\n" + "=" * 70)
        print("All connect() context manager tests passed! ✓")
        print("=" * 70)
        return 0
    except Exception as e:
        print(f"\n✗ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        loop.close()


if __name__ == "__main__":
    sys.exit(run_all_tests())
