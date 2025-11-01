import pytest
from unittest.mock import patch, MagicMock
from pytidb import TiDBClient


def test_tidb_client_connect_with_ca_path():
    """Test TiDBClient.connect() passes ca_path parameter to build_tidb_connection_url"""
    with patch("pytidb.client.build_tidb_connection_url") as mock_build_url, \
         patch("pytidb.client.create_engine") as mock_create_engine:

        # Mock the URL building and engine creation
        mock_build_url.return_value = "mysql+pymysql://user:pass@host:4000/db?ssl_ca=%2Fpath%2Fto%2Fca.pem"
        mock_engine = MagicMock()
        mock_engine.url.host = "localhost"
        mock_create_engine.return_value = mock_engine

        # Test ca_path parameter is passed through
        TiDBClient.connect(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            username="user.root",
            password="password",
            database="test_db",
            ca_path="/path/to/ca-cert.pem"
        )

        # Verify build_tidb_connection_url was called with ca_path
        mock_build_url.assert_called_once_with(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="user.root",
            password="password",
            database="test_db",
            enable_ssl=None,
            ca_path="/path/to/ca-cert.pem"
        )


def test_tidb_client_connect_without_ca_path():
    """Test TiDBClient.connect() works without ca_path (backward compatibility)"""
    with patch("pytidb.client.build_tidb_connection_url") as mock_build_url, \
         patch("pytidb.client.create_engine") as mock_create_engine:

        # Mock the URL building and engine creation
        mock_build_url.return_value = "mysql+pymysql://user:pass@host:4000/db"
        mock_engine = MagicMock()
        mock_engine.url.host = "localhost"
        mock_create_engine.return_value = mock_engine

        # Test without ca_path parameter
        TiDBClient.connect(
            host="localhost",
            username="root",
            password="password",
            database="test_db"
        )

        # Verify build_tidb_connection_url was called with None ca_path
        mock_build_url.assert_called_once_with(
            host="localhost",
            port=4000,
            username="root",
            password="password",
            database="test_db",
            enable_ssl=None,
            ca_path=None
        )


def test_tidb_client_connect_with_url_provided():
    """Test TiDBClient.connect() skips URL building when url is provided"""
    with patch("pytidb.client.build_tidb_connection_url") as mock_build_url, \
         patch("pytidb.client.create_engine") as mock_create_engine:

        # Mock engine creation
        mock_engine = MagicMock()
        mock_engine.url.host = "localhost"
        mock_create_engine.return_value = mock_engine

        # Test with URL provided (should not call build_tidb_connection_url)
        TiDBClient.connect(
            url="mysql+pymysql://user:pass@host:4000/db?ssl_ca=%2Fpath%2Fto%2Fca.pem",
            ca_path="/path/to/ca-cert.pem"  # This should be ignored
        )

        # Verify build_tidb_connection_url was NOT called
        mock_build_url.assert_not_called()

        # Verify create_engine was called with the provided URL
        mock_create_engine.assert_called_once()
        args, kwargs = mock_create_engine.call_args
        assert args[0] == "mysql+pymysql://user:pass@host:4000/db?ssl_ca=%2Fpath%2Fto%2Fca.pem"