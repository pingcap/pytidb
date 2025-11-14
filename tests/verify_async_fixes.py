#!/usr/bin/env python3
"""
Standalone verification script for P0 and P1 fixes.

This script verifies both fixes work correctly without needing pytest or database connections.
"""

from unittest.mock import MagicMock, patch
from pytidb import AsyncTiDBClient, AsyncTable
from pytidb.schema import TableModel, Field


class User(TableModel):
    __tablename__ = "users"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=100)


def test_p1_engine_sync():
    """Verify P1 fix: db_engine stays in sync."""
    print("\n=== Testing P1: Engine State Synchronization ===")

    # Setup
    mock_sync_client = MagicMock()
    mock_engine1 = MagicMock()
    mock_engine1.url.database = "test"
    mock_sync_client.db_engine = mock_engine1
    mock_sync_client._reconnect_params = {}

    # Create async client
    async_client = AsyncTiDBClient(mock_sync_client)

    # Test initial engine
    assert async_client.db_engine.url.database == "test"
    print("✓ Initial engine: test")

    # Simulate use_database changing engine (P1 fix)
    mock_engine2 = MagicMock()
    mock_engine2.url.database = "production"
    mock_sync_client.db_engine = mock_engine2

    # Should reflect new engine (dynamic property)
    assert async_client.db_engine.url.database == "production"
    print("✓ Engine updated to: production")

    # Verify no cached attribute
    assert not hasattr(async_client, "_db_engine")
    print("✓ No cached _db_engine attribute")

    return True


def test_p0_async_table_constructor():
    """Verify P0 fix: AsyncTable constructor supports both paths."""
    print("\n=== Testing P0: AsyncTable Constructor Parity ===")

    # Setup
    mock_sync_client = MagicMock()
    mock_engine = MagicMock()
    mock_engine.url.host = "localhost"
    mock_sync_client.db_engine = mock_engine
    mock_sync_client._reconnect_params = {}

    async_client = AsyncTiDBClient(mock_sync_client)

    # Test 1: sync_table path (backward compatible)
    print("\nTest 1: AsyncTable(sync_table=...)")
    mock_sync_table = MagicMock()
    mock_sync_table.table_model = User
    mock_sync_table.table_name = "users"

    async_table1 = AsyncTable(sync_table=mock_sync_table)
    assert async_table1.table_name == "users"
    print("✓ Works correctly")

    # Test 2: client+schema path (new P0 fix)
    print("\nTest 2: AsyncTable(client=..., schema=...)")
    with patch("pytidb.async_client.Table") as mock_table_class:
        mock_sync_table2 = MagicMock()
        mock_sync_table2.table_model = User
        mock_sync_table2.table_name = "users"
        mock_table_class.return_value = mock_sync_table2

        async_table2 = AsyncTable(client=async_client, schema=User)

        assert async_table2.table_name == "users"
        print("✓ Works correctly")

        # Verify Table was called with correct args
        mock_table_class.assert_called_once()
        call_kwargs = mock_table_class.call_args.kwargs
        assert call_kwargs["schema"] == User
        assert call_kwargs["client"] == mock_sync_client
        print("✓ Table instantiated with correct arguments")

    # Test 3: error handling
    print("\nTest 3: Error handling")
    try:
        AsyncTable()
        assert False, "Should have raised ValueError"
    except ValueError:
        print("✓ ValueError for missing parameters")

    try:
        AsyncTable(client=MagicMock(), schema=User)
        assert False, "Should have raised TypeError"
    except TypeError as e:
        assert "AsyncTiDBClient" in str(e)
        print("✓ TypeError for wrong client type")

    return True


def test_both_fixes_together():
    """Test P0 and P1 fixes work together."""
    print("\n=== Testing Both Fixes Together ===")

    # Setup
    mock_sync_client = MagicMock()
    mock_engine = MagicMock()
    mock_engine.url.database = "test"
    mock_sync_client.db_engine = mock_engine
    mock_sync_client._reconnect_params = {}

    async_client = AsyncTiDBClient(mock_sync_client)

    # P1: Change engine
    new_engine = MagicMock()
    new_engine.url.database = "production"
    mock_sync_client.db_engine = new_engine

    assert async_client.db_engine.url.database == "production"
    print("✓ P1: Engine synced correctly")

    # P0: Create AsyncTable with changed engine context
    with patch("pytidb.async_client.Table") as mock_table_class:
        mock_sync_table = MagicMock()
        mock_sync_table.table_model = User
        mock_sync_table.table_name = "users"
        mock_table_class.return_value = mock_sync_table

        async_table = AsyncTable(client=async_client, schema=User)
        assert async_table.table_name == "users"
        print("✓ P0: AsyncTable(client=..., schema=...) works")

    # Verify engine is still correct
    assert async_client.db_engine.url.database == "production"
    print("✓ P1: Engine still correct after AsyncTable creation")

    return True


def test_async_table_operations():
    """Test that AsyncTable operations work."""
    print("\n=== Testing AsyncTable Operations ===")

    mock_sync_table = MagicMock()
    mock_sync_table.table_model = User
    mock_sync_table.table_name = "users"

    async_table = AsyncTable(sync_table=mock_sync_table)

    # Mock async operations
    mock_record = MagicMock()
    mock_record.id = 1
    mock_record.name = "Alice"
    mock_sync_table.insert = MagicMock(return_value=mock_record)

    # Can't actually run async in sync test, but we can verify methods exist
    assert hasattr(async_table, "insert")
    assert hasattr(async_table, "query")
    assert hasattr(async_table, "get")
    assert hasattr(async_table, "update")
    assert hasattr(async_table, "delete")
    print("✓ All async methods exist")

    return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("PyTiDB Asyncio Fixes - Verification Script")
    print("=" * 60)

    tests = [
        ("P1: Engine State Synchronization", test_p1_engine_sync),
        ("P0: AsyncTable Constructor Parity", test_p0_async_table_constructor),
        ("P0+P1: Combined Fixes", test_both_fixes_together),
        ("AsyncTable Operations", test_async_table_operations),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, True, None))
        except Exception as e:
            print(f"\n✗ {name} FAILED: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False, str(e)))

    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    for name, passed, error in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed, _ in results)

    if all_passed:
        print("\n✓✓✓ ALL FIXES VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("\n✗✗✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
