"""
Integration tests for async PyTiDB functionality.
"""
import asyncio
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any

from pytidb.async_client import AsyncTiDBClient
from pytidb.async_table import AsyncTable
from pytidb.client import TiDBClient
from pytidb.table import Table
from pytidb.result import QueryResult, SQLQueryResult


class TestAsyncIntegration:
    """Integration tests for async PyTiDB functionality."""

    @pytest.fixture
    def mock_engine(self):
        """Create a mock SQLAlchemy engine."""
        engine = Mock()
        engine.url.host = "localhost"
        engine.dialect.identifier_preparer = Mock()
        return engine

    @pytest.fixture
    def mock_sync_client(self, mock_engine):
        """Create a mock TiDBClient for integration testing."""
        client = Mock(spec=TiDBClient)
        client._db_engine = mock_engine
        client._reconnect_params = {}
        client._is_serverless = False
        return client

    @pytest.fixture
    def mock_sync_table(self):
        """Create a mock Table for integration testing."""
        table = Mock(spec=Table)
        table.name = "users"
        return table

    @pytest.mark.asyncio
    async def test_full_async_workflow(self, mock_sync_client, mock_sync_table):
        """Test complete async workflow from connection to data operations."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Setup mocks
            mock_connect.return_value = mock_sync_client
            mock_sync_client.get_table.return_value = mock_sync_table

            # Mock table operations
            mock_insert_result = Mock()
            mock_select_result = Mock(spec=QueryResult)
            mock_update_result = Mock()
            mock_delete_result = Mock()

            mock_sync_table.insert.return_value = mock_insert_result
            mock_sync_table.select.return_value = mock_select_result
            mock_sync_table.update.return_value = mock_update_result
            mock_sync_table.delete.return_value = mock_delete_result

            # Execute async workflow
            async with AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                database="test_db"
            ) as client:
                # Get table
                users_table = await client.get_table("users")
                assert isinstance(users_table, AsyncTable)

                # Insert data
                user_data = {"name": "John Doe", "age": 25, "email": "john@example.com"}
                insert_result = await users_table.insert(user_data)
                assert insert_result == mock_insert_result

                # Select data
                select_result = await users_table.select(filters={"age": {"$gt": 18}})
                assert select_result == mock_select_result

                # Update data
                update_result = await users_table.update(
                    {"status": "active"},
                    filters={"age": {"$gt": 18}}
                )
                assert update_result == mock_update_result

                # Delete data
                delete_result = await users_table.delete(filters={"status": "inactive"})
                assert delete_result == mock_delete_result

            # Verify all operations were called
            mock_connect.assert_called_once()
            mock_sync_client.get_table.assert_called_once_with("users")
            mock_sync_table.insert.assert_called_once_with(user_data)
            mock_sync_table.select.assert_called_once_with(filters={"age": {"$gt": 18}})
            mock_sync_table.update.assert_called_once_with(
                {"status": "active"},
                filters={"age": {"$gt": 18}}
            )
            mock_sync_table.delete.assert_called_once_with(filters={"status": "inactive"})

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, mock_sync_client, mock_sync_table):
        """Test concurrent operations across different tables."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Setup mocks
            mock_connect.return_value = mock_sync_client

            # Create multiple mock tables
            mock_users_table = Mock(spec=Table)
            mock_products_table = Mock(spec=Table)
            mock_orders_table = Mock(spec=Table)

            def get_table_side_effect(table_name):
                if table_name == "users":
                    return mock_users_table
                elif table_name == "products":
                    return mock_products_table
                elif table_name == "orders":
                    return mock_orders_table
                return None

            mock_sync_client.get_table.side_effect = get_table_side_effect

            # Setup table operation results
            mock_users_table.insert.return_value = Mock()
            mock_products_table.select.return_value = Mock(spec=QueryResult)
            mock_orders_table.update.return_value = Mock()

            # Execute concurrent operations
            async with AsyncTiDBClient.connect(
                host="localhost",
                database="test_db"
            ) as client:
                # Get all tables
                users_table = await client.get_table("users")
                products_table = await client.get_table("products")
                orders_table = await client.get_table("orders")

                # Run concurrent operations
                tasks = [
                    users_table.insert({"name": "New User", "age": 25}),
                    products_table.select(filters={"price": {"$lt": 100}}),
                    orders_table.update({"status": "shipped"}, filters={"date": {"$gt": "2024-01-01"}})
                ]

                results = await asyncio.gather(*tasks)

                # Verify results
                assert len(results) == 3
                assert results[0] == mock_users_table.insert.return_value
                assert results[1] == mock_products_table.select.return_value
                assert results[2] == mock_orders_table.update.return_value

            # Verify all operations were called
            assert mock_sync_client.get_table.call_count == 3
            mock_users_table.insert.assert_called_once()
            mock_products_table.select.assert_called_once()
            mock_orders_table.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_like_behavior(self, mock_sync_client):
        """Test transaction-like behavior in async context."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Setup mocks
            mock_connect.return_value = mock_sync_client

            # Mock SQL execution results
            mock_begin_result = Mock()
            mock_insert_result = Mock()
            mock_update_result = Mock()
            mock_commit_result = Mock()

            mock_sync_client.execute_sql.side_effect = [
                mock_begin_result,
                mock_insert_result,
                mock_update_result,
                mock_commit_result
            ]

            # Execute transaction-like operations
            async with AsyncTiDBClient.connect(
                host="localhost",
                database="test_db"
            ) as client:
                # Simulate transaction
                await client.execute_sql("BEGIN")
                await client.execute_sql("INSERT INTO users (name) VALUES ('John')")
                await client.execute_sql("UPDATE accounts SET balance = balance - 100")
                await client.execute_sql("COMMIT")

            # Verify all SQL operations were called
            assert mock_sync_client.execute_sql.call_count == 4
            mock_sync_client.execute_sql.assert_any_call("BEGIN")
            mock_sync_client.execute_sql.assert_any_call("INSERT INTO users (name) VALUES ('John')")
            mock_sync_client.execute_sql.assert_any_call("UPDATE accounts SET balance = balance - 100")
            mock_sync_client.execute_sql.assert_any_call("COMMIT")

    @pytest.mark.asyncio
    async def test_error_recovery_in_async_workflow(self, mock_sync_client, mock_sync_table):
        """Test error recovery in async workflow."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            from pytidb.errors import TiDBError

            # Setup mocks
            mock_connect.return_value = mock_sync_client
            mock_sync_client.get_table.return_value = mock_sync_table

            # Make insert fail but select succeed
            mock_sync_table.insert.side_effect = TiDBError("Insert failed")
            mock_select_result = Mock(spec=QueryResult)
            mock_sync_table.select.return_value = mock_select_result

            # Execute workflow with error handling
            async with AsyncTiDBClient.connect(
                host="localhost",
                database="test_db"
            ) as client:
                users_table = await client.get_table("users")

                # This should fail
                with pytest.raises(TiDBError, match="Insert failed"):
                    await users_table.insert({"name": "Invalid User"})

                # This should succeed
                select_result = await users_table.select()
                assert select_result == mock_select_result

            # Verify operations
            mock_sync_client.get_table.assert_called_once_with("users")
            mock_sync_table.insert.assert_called_once()
            mock_sync_table.select.assert_called_once()

    @pytest.mark.asyncio
    async def test_performance_comparison_simulation(self):
        """Test that demonstrates potential performance benefits of async operations."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Setup mock client
            mock_sync_client = Mock(spec=TiDBClient)
            mock_connect.return_value = mock_sync_client

            # Mock slow database operations
            async def slow_sql_operation(sql):
                await asyncio.sleep(0.01)  # Simulate 10ms delay
                return Mock(spec=QueryResult)

            mock_sync_client.execute_sql.side_effect = lambda sql: Mock(spec=QueryResult)

            # Measure sequential vs concurrent execution
            queries = [f"SELECT * FROM table_{i}" for i in range(10)]

            # Sequential execution (simulated)
            start_time = asyncio.get_event_loop().time()
            for query in queries:
                await asyncio.sleep(0.01)  # Simulate sync delay
            sequential_time = asyncio.get_event_loop().time() - start_time

            # Concurrent execution
            start_time = asyncio.get_event_loop().time()
            tasks = [asyncio.sleep(0.01) for _ in queries]  # Simulate concurrent operations
            await asyncio.gather(*tasks)
            concurrent_time = asyncio.get_event_loop().time() - start_time

            # Concurrent should be faster than sequential
            assert concurrent_time < sequential_time * 0.5  # At least 50% faster

    @pytest.mark.asyncio
    async def test_connection_pool_simulation(self, mock_sync_client):
        """Test connection pool behavior simulation."""
        with patch('pytidb.async_client.TiDBClient.connect') as mock_connect:
            # Setup multiple mock clients to simulate connection pool
            clients = []
            for i in range(5):
                mock_client = Mock(spec=TiDBClient)
                mock_client._db_engine = Mock()
                mock_client._reconnect_params = {}
                mock_client._is_serverless = False
                mock_client.execute_sql.return_value = Mock(spec=QueryResult)
                clients.append(mock_client)

            mock_connect.side_effect = clients

            # Simulate connection pool usage
            async def use_connection(connection_id):
                async with AsyncTiDBClient.connect(
                    host="localhost",
                    database=f"db_{connection_id}"
                ) as client:
                    result = await client.execute_sql(f"SELECT * FROM connection_{connection_id}")
                    return result

            # Use multiple connections concurrently
            tasks = [use_connection(i) for i in range(5)]
            results = await asyncio.gather(*tasks)

            # Verify all connections were used
            assert len(results) == 5
            assert mock_connect.call_count == 5
            for i, client in enumerate(clients):
                client.execute_sql.assert_called_once_with(f"SELECT * FROM connection_{i}")