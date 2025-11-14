#!/usr/bin/env python3
"""
Test exception propagation in async session context manager.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from unittest.mock import Mock, patch, MagicMock
from pytidb.async_client import AsyncTiDBClient


async def test_session_exception_propagation():
    """Test that exceptions are properly propagated to the sync context manager."""
    print("Testing exception propagation in async session...")

    # Track what the mock __exit__ method received
    exit_calls = []

    def mock_exit_method(exc_type, exc_val, exc_tb):
        """Mock __exit__ method that records calls."""
        exit_calls.append({
            'exc_type': exc_type,
            'exc_val': exc_val,
            'exc_tb': exc_tb
        })
        return False  # Don't suppress exceptions

    with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
        # Setup mock sync client
        mock_sync_client = Mock()
        mock_sync_client._db_engine = Mock()
        mock_sync_client._reconnect_params = {}
        mock_sync_client._is_serverless = False
        mock_sync_client.disconnect = Mock()

        # Setup mock session context manager
        mock_session = Mock()
        mock_sync_client.session = Mock(return_value=mock_session)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(side_effect=mock_exit_method)

        mock_connect.return_value = mock_sync_client

        client = await AsyncTiDBClient.connect()

        # Test 1: No exception
        print("  Test 1: No exception...")
        async with client.session() as session:
            assert session == mock_session

        assert len(exit_calls) == 1
        assert exit_calls[0]['exc_type'] is None
        assert exit_calls[0]['exc_val'] is None
        assert exit_calls[0]['exc_tb'] is None
        print("  ✓ __exit__ received None, None, None (no exception)")

        exit_calls.clear()

        # Test 2: Exception occurred
        print("  Test 2: Exception occurred...")
        test_exception = ValueError("Test error")
        try:
            async with client.session() as session:
                assert session == mock_session
                raise test_exception
        except ValueError as e:
            assert e == test_exception
            print("  ✓ Exception was raised correctly")

        assert len(exit_calls) == 1
        assert exit_calls[0]['exc_type'] is ValueError
        assert exit_calls[0]['exc_val'] == test_exception
        assert exit_calls[0]['exc_tb'] is not None
        print("  ✓ __exit__ received exception info correctly")

        # Verify the __exit__ was called on the mock (not our wrapper)
        assert mock_session.__enter__.call_count == 2
        assert mock_session.__exit__.call_count == 2
        print("  ✓ __enter__ and __exit__ called correct number of times")

        print("✓ Exception propagation test passed!")


def run_all_tests():
    """Run all exception propagation tests."""
    print("=" * 60)
    print("Testing Exception Propagation in Async Session")
    print("=" * 60)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(test_session_exception_propagation())
        print("\n" + "=" * 60)
        print("All exception propagation tests passed! ✓")
        print("=" * 60)
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
