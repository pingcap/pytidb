"""Unit tests for MCP server CA path configuration"""
import os
from unittest.mock import Mock, patch, MagicMock
from pytidb.ext.mcp.server import TiDBConnector
from pytidb.utils import build_tidb_connection_url


def test_build_tidb_connection_url_with_ssl_ca():
    """Test building connection URL with ssl_ca parameter"""
    # Test with ssl_ca parameter
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user",
        password="pass",
        ssl_ca="/path/to/ca.pem",
    )
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in url
    assert "ssl_verify_cert=true" in url
    assert "ssl_verify_identity=true" in url

    # Test with ssl_ca and custom enable_ssl=False
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        enable_ssl=False,
        ssl_ca="/path/to/ca.pem",
    )
    # ssl_ca should still be added even if enable_ssl=False
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in url


def test_build_tidb_connection_url_with_ssl_ca_serverless():
    """Test SSL CA with TiDB Serverless host"""
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
        ssl_ca="/path/to/ca.pem",
    )
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in url
    assert "ssl_verify_cert=true" in url
    assert "ssl_verify_identity=true" in url
    assert url.startswith("mysql+pymysql://")


def test_tidb_connector_accepts_ca_path():
    """Test that TiDBConnector accepts ca_path parameter"""
    with patch("pytidb.ext.mcp.server.TiDBClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.connect.return_value = mock_client
        mock_client.query.return_value = Mock(to_list=lambda: [])

        connector = TiDBConnector(
            host="localhost",
            port=4000,
            username="root",
            password="",
            database="test",
            ca_path="/path/to/ca.pem",
        )

        # Verify connect was called with ssl_ca parameter
        mock_client_class.connect.assert_called_once()
        call_kwargs = mock_client_class.connect.call_args.kwargs
        assert call_kwargs.get("ssl_ca") == "/path/to/ca.pem"
        assert connector.ca_path == "/path/to/ca.pem"


def test_switch_database_with_ca_path():
    """Test that switch_database preserves CA path"""
    with patch("pytidb.ext.mcp.server.TiDBClient") as mock_client_class:
        mock_client = Mock()
        mock_client_class.connect.return_value = mock_client
        mock_client.query.return_value = Mock(to_list=lambda: [])
        mock_client.list_tables.return_value = []

        connector = TiDBConnector(
            host="localhost",
            port=4000,
            username="root",
            password="",
            database="test",
            ca_path="/path/to/ca.pem",
        )

        # Switch database
        connector.switch_database("newdb")

        # Verify connect was called again with same ssl_ca
        assert mock_client_class.connect.call_count == 2
        call_kwargs = mock_client_class.connect.call_args.kwargs
        assert call_kwargs.get("ssl_ca") == "/path/to/ca.pem"


def test_app_lifespan_reads_tidb_ca_path():
    """Test that app_lifespan reads TIDB_CA_PATH environment variable"""
    with patch("pytidb.ext.mcp.server.TiDBConnector") as mock_connector_class, \
         patch.dict(os.environ, {"TIDB_CA_PATH": "/path/to/ca.pem"}):

        mock_connector = Mock()
        mock_connector_class.return_value = mock_connector

        from pytidb.ext.mcp.server import app_lifespan
        from mcp.server.fastmcp import FastMCP

        app = FastMCP("test")

        async def test_lifespan():
            async with app_lifespan(app) as context:
                assert context.tidb == mock_connector

            # Verify TiDBConnector was called with correct parameters
            mock_connector_class.assert_called_once()
            call_kwargs = mock_connector_class.call_args.kwargs
            assert call_kwargs.get("ca_path") == "/path/to/ca.pem"

        import asyncio
        asyncio.run(test_lifespan())

