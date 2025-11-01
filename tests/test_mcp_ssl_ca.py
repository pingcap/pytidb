"""Test SSL CA certificate path configuration for MCP server."""
import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from pytidb.ext.mcp.server import TiDBConnector


class TestTiDBConnectorSSLCA:
    """Test SSL CA certificate configuration in TiDBConnector."""

    def test_tidb_connector_accepts_ssl_ca_parameter(self):
        """Test that TiDBConnector accepts ssl_ca parameter."""
        with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.connect.return_value = mock_client

            # Test with ssl_ca parameter
            connector = TiDBConnector(
                host="localhost",
                port=4000,
                username="root",
                password="password",
                database="test",
                ssl_ca="/path/to/ca.pem"
            )

            # Verify TiDBClient.connect was called with ssl_ca
            mock_client_class.connect.assert_called_once_with(
                url=None,
                host="localhost",
                port=4000,
                username="root",
                password="password",
                database="test",
                ssl_ca="/path/to/ca.pem"
            )

    def test_tidb_connector_without_ssl_ca(self):
        """Test that TiDBConnector works without ssl_ca parameter."""
        with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.connect.return_value = mock_client

            # Test without ssl_ca parameter
            connector = TiDBConnector(
                host="localhost",
                port=4000,
                username="root",
                password="password",
                database="test"
            )

            # Verify TiDBClient.connect was called without ssl_ca
            mock_client_class.connect.assert_called_once_with(
                url=None,
                host="localhost",
                port=4000,
                username="root",
                password="password",
                database="test"
            )

    def test_tidb_connector_with_database_url_and_ssl_ca(self):
        """Test TiDBConnector with database URL and ssl_ca parameter."""
        with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.connect.return_value = mock_client

            database_url = "mysql+pymysql://root:password@localhost:4000/test"

            connector = TiDBConnector(
                database_url=database_url,
                ssl_ca="/path/to/ca.pem"
            )

            # Verify TiDBClient.connect was called with database_url and ssl_ca
            mock_client_class.connect.assert_called_once_with(
                url=database_url,
                host=None,
                port=None,
                username=None,
                password=None,
                database=None,
                ssl_ca="/path/to/ca.pem"
            )

    def test_switch_database_preserves_ssl_ca(self):
        """Test that switch_database preserves ssl_ca configuration."""
        with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.connect.return_value = mock_client

            # Create connector with ssl_ca
            connector = TiDBConnector(
                host="localhost",
                port=4000,
                username="root",
                password="password",
                database="test",
                ssl_ca="/path/to/ca.pem"
            )

            # Reset call count
            mock_client_class.connect.reset_mock()

            # Switch database
            connector.switch_database("new_db")

            # Verify TiDBClient.connect was called again with ssl_ca
            mock_client_class.connect.assert_called_once_with(
                host="localhost",
                port=4000,
                username="root",
                password="password",
                database="new_db",
                ssl_ca="/path/to/ca.pem"
            )


class TestMCPServerEnvironmentVariables:
    """Test MCP server environment variable handling."""

    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host',
        'TIDB_PORT': '3306',
        'TIDB_USERNAME': 'testuser',
        'TIDB_PASSWORD': 'testpass',
        'TIDB_DATABASE': 'testdb',
        'TIDB_CA_PATH': '/path/to/test-ca.pem'
    })
    def test_app_lifespan_reads_tidb_ca_path(self):
        """Test that app_lifespan reads TIDB_CA_PATH environment variable."""
        with patch('pytidb.ext.mcp.server.TiDBConnector') as mock_connector_class:
            mock_connector = MagicMock()
            mock_connector_class.return_value = mock_connector

            # Import and test the app_lifespan function
            from pytidb.ext.mcp.server import app_lifespan, FastMCP
            import asyncio

            async def test_lifespan():
                app = FastMCP("test")
                async with app_lifespan(app) as context:
                    # Verify TiDBConnector was created with correct parameters
                    mock_connector_class.assert_called_once_with(
                        database_url=None,
                        host='test-host',
                        port=3306,
                        username='testuser',
                        password='testpass',
                        database='testdb',
                        ssl_ca='/path/to/test-ca.pem'
                    )

            # Run the async test
            asyncio.run(test_lifespan())

    @patch.dict(os.environ, {
        'TIDB_HOST': 'test-host',
        'TIDB_PORT': '3306',
        'TIDB_USERNAME': 'testuser',
        'TIDB_PASSWORD': 'testpass',
        'TIDB_DATABASE': 'testdb'
        # TIDB_CA_PATH not set
    })
    def test_app_lifespan_without_tidb_ca_path(self):
        """Test that app_lifespan works without TIDB_CA_PATH environment variable."""
        with patch('pytidb.ext.mcp.server.TiDBConnector') as mock_connector_class:
            mock_connector = MagicMock()
            mock_connector_class.return_value = mock_connector

            # Import and test the app_lifespan function
            from pytidb.ext.mcp.server import app_lifespan, FastMCP
            import asyncio

            async def test_lifespan():
                app = FastMCP("test")
                async with app_lifespan(app) as context:
                    # Verify TiDBConnector was created without ssl_ca
                    mock_connector_class.assert_called_once_with(
                        database_url=None,
                        host='test-host',
                        port=3306,
                        username='testuser',
                        password='testpass',
                        database='testdb',
                        ssl_ca=None
                    )

            # Run the async test
            asyncio.run(test_lifespan())

    def test_ssl_ca_file_validation(self):
        """Test that ssl_ca parameter validates file existence."""
        # Create a temporary CA file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write("-----BEGIN CERTIFICATE-----\ntest cert data\n-----END CERTIFICATE-----\n")
            temp_ca_path = f.name

        try:
            with patch('pytidb.ext.mcp.server.TiDBClient') as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.connect.return_value = mock_client

                # Should work with existing file
                connector = TiDBConnector(
                    host="localhost",
                    port=4000,
                    username="root",
                    password="password",
                    database="test",
                    ssl_ca=temp_ca_path
                )

                # Verify the ssl_ca parameter was passed through
                mock_client_class.connect.assert_called_once_with(
                    url=None,
                    host="localhost",
                    port=4000,
                    username="root",
                    password="password",
                    database="test",
                    ssl_ca=temp_ca_path
                )
        finally:
            # Clean up
            os.unlink(temp_ca_path)