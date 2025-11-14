"""Tests for async client functionality - Fixed for context manager pattern."""
import asyncio
import inspect
from unittest.mock import Mock, MagicMock, AsyncMock, patch, call
import pytest

from pytidb.client import TiDBClient
from pytidb.result import SQLExecuteResult, SQLQueryResult
from pytidb.async_client import AsyncSQLQueryResult


@pytest.fixture
def mock_sync_client():
    """Create a mock sync TiDBClient."""
    mock_client = Mock(spec=TiDBClient)
    mock_client.disconnect = Mock()
    mock_client.execute = Mock(return_value=SQLExecuteResult(rowcount=1, success=True))
    mock_client.query = Mock(return_value=SQLQueryResult(Mock(fetchall=lambda: [(1, "test")])))
    mock_client.list_databases = Mock(return_value=["db1", "db2"])
    mock_client.has_database = Mock(return_value=True)
    mock_client.create_database = Mock()
    mock_client.drop_database = Mock()
    mock_client.list_tables = Mock(return_value=["table1", "table2"])
    mock_client.has_table = Mock(return_value=True)
    mock_client.current_database = Mock(return_value="test_db")
    return mock_client


class TestAsyncConnection:
    """Test async connection and disconnection."""

    @pytest.mark.asyncio
    async def test_connect_creates_async_client(self):
        """Test that connect_async classmethod creates AsyncTiDBClient."""
        from pytidb.async_client import AsyncTiDBClient

        # Mock the sync client's connect method
        mock_sync_client = Mock(spec=TiDBClient)
        mock_sync_client.disconnect = Mock()

        with patch.object(TiDBClient, 'connect', return_value=mock_sync_client):
            async_client = await AsyncTiDBClient.connect_async(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            )

            assert isinstance(async_client, AsyncTiDBClient)
            TiDBClient.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_calls_sync_disconnect(self, mock_sync_client):
        """Test that async disconnect calls sync disconnect."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        await async_client.disconnect()

        mock_sync_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_enters_and_exits(self):
        """Test that async context manager works correctly with connect()."""
        from pytidb.async_client import AsyncTiDBClient

        mock_sync_client = Mock(spec=TiDBClient)
        mock_sync_client.disconnect = Mock()

        with patch.object(TiDBClient, 'connect', return_value=mock_sync_client):
            # Use connect() which returns a context manager
            async with AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            ) as client:
                assert isinstance(client, AsyncTiDBClient)

            # Verify disconnect was called on exit
            mock_sync_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_disconnects_on_exception(self):
        """Test that context manager disconnects even on exception."""
        from pytidb.async_client import AsyncTiDBClient

        mock_sync_client = Mock(spec=TiDBClient)
        mock_sync_client.disconnect = Mock()

        with patch.object(TiDBClient, 'connect', return_value=mock_sync_client):
            with pytest.raises(RuntimeError):
                async with AsyncTiDBClient.connect(
                    host="localhost",
                    port=4000,
                    username="root",
                    password="",
                    database="test"
                ) as client:
                    raise RuntimeError("Test exception")

            # Verify disconnect was still called
            mock_sync_client.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_async_direct_usage(self):
        """Test connect_async for direct non-context-manager usage."""
        from pytidb.async_client import AsyncTiDBClient

        mock_sync_client = Mock(spec=TiDBClient)
        mock_sync_client.disconnect = Mock()

        with patch.object(TiDBClient, 'connect', return_value=mock_sync_client):
            # Use connect_async() directly
            client = await AsyncTiDBClient.connect_async(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            )

            assert isinstance(client, AsyncTiDBClient)
            assert not mock_sync_client.disconnect.called

            # Manually disconnect
            await client.disconnect()
            mock_sync_client.disconnect.assert_called_once()


class TestAsyncDatabaseOperations:
    """Test async database operations."""

    @pytest.mark.asyncio
    async def test_list_databases(self, mock_sync_client):
        """Test listing databases asynchronously."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        databases = await async_client.list_databases()

        assert databases == ["db1", "db2"]
        mock_sync_client.list_databases.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_database_returns_true(self, mock_sync_client):
        """Test checking database existence (positive)."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        result = await async_client.has_database("db1")

        assert result is True
        mock_sync_client.has_database.assert_called_once_with("db1")

    @pytest.mark.asyncio
    async def test_has_database_returns_false(self, mock_sync_client):
        """Test checking database existence (negative)."""
        from pytidb.async_client import AsyncTiDBClient

        mock_sync_client.has_database.return_value = False
        async_client = AsyncTiDBClient(mock_sync_client)
        result = await async_client.has_database("nonexistent")

        assert result is False
        mock_sync_client.has_database.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_create_database(self, mock_sync_client):
        """Test creating database."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        await async_client.create_database("new_db")

        mock_sync_client.create_database.assert_called_once_with(
            "new_db", if_exists="raise"
        )

    @pytest.mark.asyncio
    async def test_create_database_if_exists_skip(self, mock_sync_client):
        """Test creating database with if_exists='skip'."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        await async_client.create_database("new_db", if_exists="skip")

        mock_sync_client.create_database.assert_called_once_with(
            "new_db", if_exists="skip"
        )

    @pytest.mark.asyncio
    async def test_drop_database(self, mock_sync_client):
        """Test dropping database."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        await async_client.drop_database("old_db")

        mock_sync_client.drop_database.assert_called_once_with("old_db")

    @pytest.mark.asyncio
    async def test_current_database(self, mock_sync_client):
        """Test getting current database."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        db = await async_client.current_database()

        assert db == "test_db"
        mock_sync_client.current_database.assert_called_once()


class TestAsyncTableOperations:
    """Test async table operations."""

    @pytest.mark.asyncio
    async def test_list_tables(self, mock_sync_client):
        """Test listing tables asynchronously."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        tables = await async_client.list_tables()

        assert tables == ["table1", "table2"]
        mock_sync_client.list_tables.assert_called_once()

    @pytest.mark.asyncio
    async def test_has_table_returns_true(self, mock_sync_client):
        """Test checking table existence."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        result = await async_client.has_table("table1")

        assert result is True
        mock_sync_client.has_table.assert_called_once_with("table1")


class TestAsyncQueryExecution:
    """Test async query execution."""

    @pytest.mark.asyncio
    async def test_execute_sql(self, mock_sync_client):
        """Test executing SQL asynchronously."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        result = await async_client.execute("INSERT INTO test VALUES (1, 'test')")

        assert isinstance(result, SQLExecuteResult)
        assert result.success is True
        assert result.rowcount == 1
        mock_sync_client.execute.assert_called_once_with(
            "INSERT INTO test VALUES (1, 'test')", params=None, raise_error=False
        )

    @pytest.mark.asyncio
    async def test_execute_sql_with_params(self, mock_sync_client):
        """Test executing SQL with parameters."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        await async_client.execute(
            "INSERT INTO test VALUES (:id, :name)",
            params={"id": 2, "name": "test2"}
        )

        mock_sync_client.execute.assert_called_once_with(
            "INSERT INTO test VALUES (:id, :name)",
            params={"id": 2, "name": "test2"},
            raise_error=False
        )

    @pytest.mark.asyncio
    async def test_query_sql(self, mock_sync_client):
        """Test querying SQL asynchronously."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        result = await async_client.query("SELECT * FROM test")

        # Verify we get AsyncSQLQueryResult, not SQLQueryResult
        assert isinstance(result, AsyncSQLQueryResult)
        mock_sync_client.query.assert_called_once_with(
            "SELECT * FROM test", params=None
        )

    @pytest.mark.asyncio
    async def test_query_sql_with_params(self, mock_sync_client):
        """Test querying SQL with parameters."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)
        await async_client.query("SELECT * FROM test WHERE id = :id", params={"id": 1})

        mock_sync_client.query.assert_called_once_with(
            "SELECT * FROM test WHERE id = :id", params={"id": 1}
        )

    @pytest.mark.asyncio
    async def test_query_result_conversion(self, mock_sync_client):
        """Test that query result can be converted to list asynchronously."""
        from pytidb.async_client import AsyncTiDBClient
        from sqlalchemy import Result

        # Create a proper SQLQueryResult with mock data
        mock_result = Mock(spec=Result)
        mock_result.keys.return_value = ["id", "name"]
        mock_result.fetchall.return_value = [(1, "test1"), (2, "test2")]
        mock_sync_client.query.return_value = SQLQueryResult(mock_result)

        async_client = AsyncTiDBClient(mock_sync_client)
        result = await async_client.query("SELECT * FROM test")

        # Verify we get AsyncSQLQueryResult
        assert isinstance(result, AsyncSQLQueryResult)

        # Convert to list asynchronously
        result_list = await result.to_list()
        assert len(result_list) == 2
        assert result_list[0] == {"id": 1, "name": "test1"}
        assert result_list[1] == {"id": 2, "name": "test2"}


class TestAsyncConcurrency:
    """Test async concurrent operations."""

    @pytest.mark.asyncio
    async def test_concurrent_queries_with_gather(self, mock_sync_client):
        """Test running multiple queries concurrently using asyncio.gather."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)

        # Track call order
        call_order = []
        original_query = mock_sync_client.query

        def track_query(*args, **kwargs):
            import time
            call_order.append("start")
            time.sleep(0.01)  # Simulate slow query
            result = original_query(*args, **kwargs)
            call_order.append("end")
            return result

        mock_sync_client.query.side_effect = track_query

        # Run three queries concurrently
        results = await asyncio.gather(
            async_client.query("SELECT 1"),
            async_client.query("SELECT 2"),
            async_client.query("SELECT 3"),
        )

        # All queries should succeed
        assert len(results) == 3
        assert all(isinstance(r, AsyncSQLQueryResult) for r in results)

        # If queries truly ran concurrently, we might see start-start-start before end
        # (though exact order depends on thread pool scheduling)
        assert len(call_order) == 6  # 3 starts + 3 ends

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, mock_sync_client):
        """Test concurrent database operations."""
        from pytidb.async_client import AsyncTiDBClient

        async_client = AsyncTiDBClient(mock_sync_client)

        # Run multiple operations concurrently
        await asyncio.gather(
            async_client.list_databases(),
            async_client.has_database("db1"),
            async_client.has_table("table1"),
            async_client.current_database(),
        )

        # All operations should be called
        mock_sync_client.list_databases.assert_called()
        mock_sync_client.has_database.assert_called()
        mock_sync_client.has_table.assert_called()
        mock_sync_client.current_database.assert_called()


class TestAsyncErrorHandling:
    """Test error handling in async context."""

    @pytest.mark.asyncio
    async def test_execute_raises_sqlalchemy_error(self, mock_sync_client):
        """Test that SQLAlchemy errors are propagated."""
        from pytidb.async_client import AsyncTiDBClient
        import sqlalchemy

        mock_sync_client.execute.side_effect = sqlalchemy.exc.SQLAlchemyError(
            "Syntax error"
        )

        async_client = AsyncTiDBClient(mock_sync_client)

        with pytest.raises(sqlalchemy.exc.SQLAlchemyError):
            await async_client.execute("INVALID SQL")

    @pytest.mark.asyncio
    async def test_query_raises_connection_error(self, mock_sync_client):
        """Test that connection errors are propagated."""
        from pytidb.async_client import AsyncTiDBClient

        mock_sync_client.query.side_effect = ConnectionError("Connection failed")

        async_client = AsyncTiDBClient(mock_sync_client)

        with pytest.raises(ConnectionError):
            await async_client.query("SELECT 1")

    @pytest.mark.asyncio
    async def test_execute_with_raise_error_false(self, mock_sync_client):
        """Test that execute with raise_error=False returns error in result."""
        from pytidb.async_client import AsyncTiDBClient
        import sqlalchemy

        mock_sync_client.execute.side_effect = sqlalchemy.exc.SQLAlchemyError(
            "Syntax error"
        )
        mock_sync_client.execute.return_value = SQLExecuteResult(
            rowcount=0, success=False, message="Syntax error"
        )

        # Reset the side_effect for this test
        mock_sync_client.execute.side_effect = None

        # This time make it return error result instead of raising
        error_result = SQLExecuteResult(
            rowcount=0, success=False, message="Syntax error"
        )
        mock_sync_client.execute.return_value = error_result

        async_client = AsyncTiDBClient(mock_sync_client)
        result = await async_client.execute("INVALID SQL", raise_error=False)

        assert result.success is False
        assert result.message == "Syntax error"


class TestContextManagerRegression:
    """Regression tests for context manager functionality."""

    @pytest.mark.asyncio
    async def test_connect_returns_context_manager_not_coroutine(self):
        """Regression test: connect() should return a context manager, not a coroutine."""
        from pytidb.async_client import AsyncTiDBClient, _AsyncClientContext

        # connect() should return a context manager immediately (not a coroutine)
        context = AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            username="root",
            password="",
            database="test"
        )

        # Should not be a coroutine
        assert not asyncio.iscoroutine(context)
        # Should be a context manager
        assert isinstance(context, _AsyncClientContext)
        # Should have __aenter__ and __aexit__
        assert hasattr(context, '__aenter__')
        assert hasattr(context, '__aexit__')

        # This would have caused: TypeError: object _AsyncClientContext can't be used in 'await' expression
        # when we incorrectly made connect() async

    @pytest.mark.asyncio
    async def test_context_manager_cleanup_on_success(self):
        """Test that context manager properly cleans up on successful exit."""
        from pytidb.async_client import AsyncTiDBClient

        mock_sync_client = Mock(spec=TiDBClient)
        mock_sync_client.disconnect = Mock()

        with patch.object(TiDBClient, 'connect', return_value=mock_sync_client):
            async with AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            ) as client:
                assert isinstance(client, AsyncTiDBClient)
                # Do some operations
                await client.list_databases()

            # Verify disconnect was called exactly once after context exit
            assert mock_sync_client.disconnect.call_count == 1

    @pytest.mark.asyncio
    async def test_context_manager_no_cleanup_if_not_entered(self):
        """Test that cleanup doesn't happen if context is not entered."""
        from pytidb.async_client import AsyncTiDBClient

        mock_sync_client = Mock(spec=TiDBClient)
        mock_sync_client.disconnect = Mock()

        with patch.object(TiDBClient, 'connect', return_value=mock_sync_client):
            # Create context but don't enter it
            context = AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="test"
            )

            # Disconnect should not be called yet
            assert not mock_sync_client.disconnect.called

            # Now enter and exit
            async with context as client:
                pass

            # Now it should be called
            assert mock_sync_client.disconnect.call_count == 1
