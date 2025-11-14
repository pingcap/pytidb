"""
Configuration for async tests.

This module provides fixtures and configuration specific to async tests,
avoiding the need for real database connections.
"""
import pytest
from unittest.mock import Mock, patch


@pytest.fixture(autouse=True, scope="session")
def mock_database_connections():
    """
    Mock all database connections for async tests.

    This fixture prevents async tests from attempting to connect
    to real databases by mocking the connection creation process.
    """
    with patch('pytidb.client.TiDBClient.connect') as mock_connect:
        # Create a mock client that doesn't need real database
        mock_client = Mock()
        mock_client._db_engine = Mock()
        mock_client._reconnect_params = {}
        mock_client._is_serverless = False
        mock_client.disconnect = Mock()
        mock_client.execute_sql = Mock()
        mock_client.execute = Mock()
        mock_client.get_table = Mock()
        mock_client.use_database = Mock()
        mock_client.create_database = Mock()
        mock_client.drop_database = Mock()
        mock_client.database_exists = Mock()
        mock_client.list_databases = Mock()
        mock_client.list_tables = Mock()

        mock_connect.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_sync_result():
    """Create a mock SQLQueryResult for testing."""
    result = Mock()
    result.scalar.return_value = 42
    result.one.return_value = {"id": 1, "name": "John"}
    result.fetchall.return_value = [
        (1, "John", 25),
        (2, "Jane", 30)
    ]
    result.keys.return_value = ["id", "name", "age"]
    result.to_list.return_value = [
        {"id": 1, "name": "John", "age": 25},
        {"id": 2, "name": "Jane", "age": 30}
    ]
    result.to_pandas.return_value = Mock()
    return result


@pytest.fixture
def mock_sync_table():
    """Create a mock Table for testing."""
    table = Mock()
    table.name = "users"
    table.insert = Mock()
    table.select = Mock()
    table.update = Mock()
    table.delete = Mock()
    table.search = Mock()
    table.count = Mock()
    table.exists = Mock()
    table.create_index = Mock()
    table.drop_index = Mock()
    table.truncate = Mock()
    return table