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