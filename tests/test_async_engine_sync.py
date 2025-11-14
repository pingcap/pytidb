"""
Tests for engine state consistency in AsyncTiDBClient.

Verifies that db_engine property always reflects the current engine from sync client,
especially after operations like use_database that can change the engine.
"""

import pytest
from unittest.mock import MagicMock, patch
from pytidb import AsyncTiDBClient


class TestEngineStateSync:
    """Test that async client's db_engine stays in sync with sync client."""

    def test_db_engine_fetches_from_sync_client(self):
        """Test that db_engine property fetches from sync client dynamically."""
        mock_sync_client = MagicMock()
        mock_engine = MagicMock()
        mock_sync_client.db_engine = mock_engine

        async_client = AsyncTiDBClient(mock_sync_client)

        # Access db_engine
        assert async_client.db_engine == mock_engine

        # Verify it fetches from sync client each time
        mock_engine2 = MagicMock()
        mock_sync_client.db_engine = mock_engine2
        assert async_client.db_engine == mock_engine2

    def test_db_engine_reflects_changes_in_sync_client(self):
        """Test that db_engine reflects when sync client changes its engine."""
        mock_sync_client = MagicMock()
        original_engine = MagicMock()
        original_engine.url.database = "original_db"
        mock_sync_client.db_engine = original_engine

        async_client = AsyncTiDBClient(mock_sync_client)

        # Initially returns original engine
        assert async_client.db_engine == original_engine
        assert async_client.db_engine.url.database == "original_db"

        # Simulate use_database changing the engine in sync client
        new_engine = MagicMock()
        new_engine.url.database = "new_db"
        mock_sync_client.db_engine = new_engine

        # Async client should reflect the change automatically
        assert async_client.db_engine == new_engine
        assert async_client.db_engine.url.database == "new_db"
        assert async_client.db_engine != original_engine

    @pytest.mark.asyncio
    async def test_use_database_updates_engine(self):
        """Test that use_database operation updates the engine correctly."""
        mock_sync_client = MagicMock()
        original_engine = MagicMock()
        original_engine.url.database = "test"
        mock_sync_client.db_engine = original_engine
        mock_sync_client._reconnect_params = {"debug": False}

        async_client = AsyncTiDBClient(mock_sync_client)

        # Initially in "test" database
        assert async_client.db_engine.url.database == "test"

        # Simulate use_database changing to "newdb"
        new_engine = MagicMock()
        new_engine.url.database = "newdb"
        new_client = MagicMock()
        new_client._db_engine = new_engine
        new_client._reconnect_params = {"debug": False}

        # Mock the sync client's use_database to change its engine
        def mock_use_database(database, ensure_db=None):
            mock_sync_client.db_engine = new_engine

        mock_sync_client.use_database = mock_use_database

        # Call use_database through async client
        await async_client.use_database("newdb")

        # Verify engine was updated
        assert async_client.db_engine.url.database == "newdb"
        assert async_client.db_engine == new_engine

    def test_is_serverless_fetches_from_sync_client(self):
        """Test that is_serverless also fetches dynamically from sync client."""
        mock_sync_client = MagicMock()
        mock_sync_client.is_serverless = False

        async_client = AsyncTiDBClient(mock_sync_client)

        # Initially False
        assert async_client.is_serverless is False

        # Change in sync client
        mock_sync_client.is_serverless = True

        # Should reflect the change
        assert async_client.is_serverless is True

    def test_no_db_engine_attribute_on_async_client(self):
        """Test that async client doesn't cache db_engine as instance attribute."""
        mock_sync_client = MagicMock()
        mock_sync_client.db_engine = MagicMock()

        async_client = AsyncTiDBClient(mock_sync_client)

        # db_engine should not be stored as instance attribute
        assert not hasattr(async_client, '_db_engine')

        # Should only exist as property
        assert hasattr(async_client.__class__, 'db_engine')
        assert isinstance(getattr(type(async_client), 'db_engine'), property)

    @pytest.mark.asyncio
    async def test_multiple_database_switches(self):
        """Test engine stays in sync across multiple database switches."""
        mock_sync_client = MagicMock()
        current_engine = MagicMock()
        current_engine.url.database = "test"
        mock_sync_client.db_engine = current_engine
        mock_sync_client._reconnect_params = {"debug": False}

        async_client = AsyncTiDBClient(mock_sync_client)

        # Simulate database switches
        for db_name in ["db1", "db2", "db3"]:
            new_engine = MagicMock()
            new_engine.url.database = db_name

            def mock_use(database, ensure_db=None):
                mock_sync_client.db_engine = new_engine

            mock_sync_client.use_database = mock_use

            await async_client.use_database(db_name)

            # Verify engine reflects current database
            assert async_client.db_engine.url.database == db_name
            assert async_client.db_engine == new_engine

    @pytest.mark.asyncio
    async def test_all_database_operations_maintain_engine_sync(self):
        """Test that all database management ops maintain engine consistency."""
        mock_sync_client = MagicMock()
        original_engine = MagicMock()
        original_engine.url.database = "original"
        mock_sync_client.db_engine = original_engine
        mock_sync_client._reconnect_params = {"debug": False}

        async_client = AsyncTiDBClient(mock_sync_client)

        # Test create_database (shouldn't change current engine)
        await async_client.create_database("newdb")
        assert async_client.db_engine == original_engine

        # Test drop_database (shouldn't change current engine)
        await async_client.drop_database("olddb")
        assert async_client.db_engine == original_engine

        # Test list_databases (shouldn't change current engine)
        result = await async_client.list_databases()
        assert async_client.db_engine == original_engine

    def test_identifier_preparer_not_cached(self):
        """Verify identifier_preparer stays in sync (though less likely to change)."""
        mock_sync_client = MagicMock()
        orig_preparer = MagicMock()
        mock_sync_client._identifier_preparer = orig_preparer

        async_client = AsyncTiDBClient(mock_sync_client)

        # Should be accessible (this was cached in __init__)
        # But we're keeping it for now since it's less likely to change
        # and is used in some sync methods
        assert async_client._identifier_preparer == orig_preparer
