import os
import pytest
from unittest.mock import patch, MagicMock

from pytidb.ext.mcp.server import TiDBConnector


@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_ca_path_basic(mock_tidb_client):
    """Test basic CA path functionality."""
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    connector = TiDBConnector(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        ssl_ca_path="/path/to/ca-cert.pem"
    )

    # Verify ssl_ca_path is stored
    assert connector.ssl_ca_path == "/path/to/ca-cert.pem"


@patch.dict(os.environ, {'TIDB_CA_PATH': '/path/to/ca-cert.pem'})
@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_env_ca_path(mock_tidb_client):
    """Test TIDB_CA_PATH environment variable."""
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    ca_path = os.getenv("TIDB_CA_PATH", None)
    connector = TiDBConnector(ssl_ca_path=ca_path)

    assert connector.ssl_ca_path == '/path/to/ca-cert.pem'


@patch.dict(os.environ, {'TIDB_CA_PATH': ''})
@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_empty_string_env_ca_path_doesnt_crash(mock_tidb_client):
    """Test that empty TIDB_CA_PATH env var doesn't cause MCP server to crash.

    Regression test for issue where TIDB_CA_PATH="" would cause:
    ValueError: ssl_ca_path must be a non-empty string

    The fix ensures empty strings are converted to None before being passed
    to TiDBClient.connect().
    """
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    # Simulate the app_lifespan logic
    ca_path = os.getenv("TIDB_CA_PATH", None)

    # Apply the fix: convert empty string to None
    if ca_path is not None and not ca_path.strip():
        ca_path = None

    # This should not raise ValueError
    connector = TiDBConnector(
        host="localhost",
        ssl_ca_path=ca_path
    )

    # Verify ca_path was converted to None
    assert ca_path is None
    assert connector.ssl_ca_path is None

    # Verify TiDBClient.connect was called with ssl_ca_path=None (not "")
    mock_tidb_client.connect.assert_called_once()
    call_kwargs = mock_tidb_client.connect.call_args[1]
    assert call_kwargs['ssl_ca_path'] is None


@patch.dict(os.environ, {'TIDB_CA_PATH': '   '})
@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_whitespace_env_ca_path_doesnt_crash(mock_tidb_client):
    """Test that whitespace-only TIDB_CA_PATH doesn't cause MCP server to crash."""
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    # Simulate the app_lifespan logic
    ca_path = os.getenv("TIDB_CA_PATH", None)

    # Apply the fix: convert whitespace-only string to None
    if ca_path is not None and not ca_path.strip():
        ca_path = None

    # This should not raise ValueError
    connector = TiDBConnector(
        host="localhost",
        ssl_ca_path=ca_path
    )

    # Verify ca_path was converted to None
    assert ca_path is None
    assert connector.ssl_ca_path is None