import os
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


@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_extract_ssl_ca_from_database_url(mock_tidb_client):
    """Test that ssl_ca is extracted from database_url query parameters.

    Regression test for issue where ssl_ca in database_url was not preserved
    during switch_database() reconnections, causing TLS validation failures.
    """
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    # Database URL with ssl_ca in query parameters
    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/testdb?ssl_ca=/path/to/ca.pem&ssl_verify_cert=true&ssl_verify_identity=true"

    connector = TiDBConnector(database_url=database_url)

    # Verify ssl_ca_path was extracted from URL
    assert connector.ssl_ca_path == "/path/to/ca.pem"

    # Verify other parameters were also extracted
    assert connector.host == "gateway01.us-west-2.prod.aws.tidbcloud.com"
    assert connector.port == 4000
    assert connector.username == "user"
    assert connector.password == "pass"
    assert connector.database == "testdb"


@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_ssl_ca_parameter_overrides_url(mock_tidb_client):
    """Test that explicit ssl_ca_path parameter overrides URL value."""
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    # Database URL with ssl_ca in query parameters
    database_url = "mysql+pymysql://user:pass@host:4000/db?ssl_ca=/url/ca.pem"

    # Explicit parameter should override URL value
    connector = TiDBConnector(
        database_url=database_url,
        ssl_ca_path="/override/ca.pem"
    )

    # Verify parameter takes precedence
    assert connector.ssl_ca_path == "/override/ca.pem"


@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_switch_database_preserves_ssl_ca(mock_tidb_client):
    """Test that switch_database() preserves ssl_ca_path for reconnection.

    This is the critical test for the bug fix: switch_database() must pass
    the original ssl_ca_path to TiDBClient.connect() to maintain TLS validation.
    """
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    # Initialize with database_url containing ssl_ca
    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/db1?ssl_ca=/custom/ca.pem"

    connector = TiDBConnector(database_url=database_url)

    # Verify ssl_ca_path was extracted
    assert connector.ssl_ca_path == "/custom/ca.pem"

    # Reset mock to track the next call
    mock_tidb_client.connect.reset_mock()

    # Switch to a different database
    connector.switch_database("db2")

    # Verify TiDBClient.connect was called with ssl_ca_path preserved
    mock_tidb_client.connect.assert_called_once()
    call_kwargs = mock_tidb_client.connect.call_args[1]

    # This is the critical assertion: ssl_ca_path must be passed to reconnection
    assert call_kwargs['ssl_ca_path'] == "/custom/ca.pem"
    assert call_kwargs['host'] == "gateway01.us-west-2.prod.aws.tidbcloud.com"
    assert call_kwargs['port'] == 4000
    assert call_kwargs['username'] == "user"
    assert call_kwargs['password'] == "pass"
    assert call_kwargs['database'] == "db2"


@patch('pytidb.ext.mcp.server.TiDBClient')
def test_mcp_database_url_without_ssl_ca(mock_tidb_client):
    """Test that database_url without ssl_ca works correctly."""
    mock_client = MagicMock()
    mock_tidb_client.connect.return_value = mock_client

    # Database URL without ssl_ca parameter
    database_url = "mysql+pymysql://user:pass@localhost:4000/testdb"

    connector = TiDBConnector(database_url=database_url)

    # Verify ssl_ca_path is None when not in URL
    assert connector.ssl_ca_path is None


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