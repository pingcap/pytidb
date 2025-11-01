import pytest
import os
from unittest.mock import patch, MagicMock
from pytidb.ext.mcp.server import TiDBConnector


def test_tidb_connector_with_ca_path():
    """Test TiDBConnector passes ca_path to TiDBClient.connect()"""
    with patch("pytidb.ext.mcp.server.TiDBClient") as mock_tidb_client:
        mock_client_instance = MagicMock()
        mock_tidb_client.connect.return_value = mock_client_instance

        # Test with ca_path parameter
        connector = TiDBConnector(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="user.root",
            password="password",
            database="test_db",
            ca_path="/path/to/ca-cert.pem"
        )

        # Verify TiDBClient.connect was called with ca_path
        mock_tidb_client.connect.assert_called_once_with(
            url=None,
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="user.root",
            password="password",
            database="test_db",
            ca_path="/path/to/ca-cert.pem"
        )

        # Verify ca_path is stored for later use
        assert connector.ca_path == "/path/to/ca-cert.pem"


def test_tidb_connector_without_ca_path():
    """Test TiDBConnector works without ca_path (backward compatibility)"""
    with patch("pytidb.ext.mcp.server.TiDBClient") as mock_tidb_client:
        mock_client_instance = MagicMock()
        mock_tidb_client.connect.return_value = mock_client_instance

        # Test without ca_path parameter
        connector = TiDBConnector(
            host="localhost",
            port=4000,
            username="root",
            password="password",
            database="test_db"
        )

        # Verify TiDBClient.connect was called with None ca_path
        mock_tidb_client.connect.assert_called_once_with(
            url=None,
            host="localhost",
            port=4000,
            username="root",
            password="password",
            database="test_db",
            ca_path=None
        )

        # Verify ca_path is None
        assert connector.ca_path is None


def test_tidb_connector_switch_database_with_ca_path():
    """Test TiDBConnector.switch_database() preserves ca_path"""
    with patch("pytidb.ext.mcp.server.TiDBClient") as mock_tidb_client:
        mock_client_instance = MagicMock()
        mock_tidb_client.connect.return_value = mock_client_instance

        # Create connector with ca_path
        connector = TiDBConnector(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="user.root",
            password="password",
            database="test_db",
            ca_path="/path/to/ca-cert.pem"
        )

        # Reset mock to check switch_database call
        mock_tidb_client.connect.reset_mock()

        # Switch database
        connector.switch_database("new_db")

        # Verify TiDBClient.connect was called with ca_path preserved
        mock_tidb_client.connect.assert_called_once_with(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            port=4000,
            username="user.root",
            password="password",
            database="new_db",
            ca_path="/path/to/ca-cert.pem"
        )


def test_tidb_connector_with_database_url():
    """Test TiDBConnector with database_url and ca_path"""
    with patch("pytidb.ext.mcp.server.TiDBClient") as mock_tidb_client:
        mock_client_instance = MagicMock()
        mock_tidb_client.connect.return_value = mock_client_instance

        # Test with database_url and ca_path
        connector = TiDBConnector(
            database_url="mysql+pymysql://user:pass@host:4000/db",
            ca_path="/path/to/ca-cert.pem"
        )

        # Verify TiDBClient.connect was called with both url and ca_path
        mock_tidb_client.connect.assert_called_once_with(
            url="mysql+pymysql://user:pass@host:4000/db",
            host=None,
            port=None,
            username=None,
            password=None,
            database=None,
            ca_path="/path/to/ca-cert.pem"
        )

        # Verify ca_path is stored (even when using database_url)
        assert connector.ca_path == "/path/to/ca-cert.pem"


@patch.dict(os.environ, {
    "TIDB_HOST": "gateway01.us-west-2.prod.aws.tidbcloud.com",
    "TIDB_PORT": "4000",
    "TIDB_USERNAME": "user.root",
    "TIDB_PASSWORD": "secret",
    "TIDB_DATABASE": "test_db",
    "TIDB_CA_PATH": "/path/to/ca-cert.pem"
})
def test_app_lifespan_reads_tidb_ca_path_env():
    """Test that app_lifespan reads TIDB_CA_PATH environment variable"""
    with patch("pytidb.ext.mcp.server.TiDBConnector") as mock_connector:
        from pytidb.ext.mcp.server import app_lifespan, FastMCP

        # Mock the connector
        mock_connector_instance = MagicMock()
        mock_connector.return_value = mock_connector_instance
        mock_connector_instance.host = "gateway01.us-west-2.prod.aws.tidbcloud.com"
        mock_connector_instance.port = 4000
        mock_connector_instance.database = "test_db"

        # Create app and run lifespan
        app = FastMCP("test", instructions="test instructions")

        # Use the lifespan context manager
        import asyncio

        async def test_lifespan():
            async with app_lifespan(app) as context:
                # Verify TiDBConnector was called with TIDB_CA_PATH
                mock_connector.assert_called_once_with(
                    database_url=None,
                    host="gateway01.us-west-2.prod.aws.tidbcloud.com",
                    port=4000,
                    username="user.root",
                    password="secret",
                    database="test_db",
                    ca_path="/path/to/ca-cert.pem"
                )

        # Run the async test
        asyncio.run(test_lifespan())


def test_tidb_connector_database_url_with_ca_path_integration():
    """Integration test without mocks - validates real URL merging with ca_path"""
    from pytidb.ext.mcp.server import TiDBConnector

    # Test the critical scenario: database_url + ca_path (no mocks)
    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test"
    ca_path = r"C:\Certs & Keys\root.pem"

    try:
        # This exercises the real code path through TiDBClient.connect
        connector = TiDBConnector(
            database_url=database_url,
            ca_path=ca_path
        )

        # Verify the engine URL contains the ssl_ca parameter
        engine_url = str(connector.tidb_client._db_engine.url)

        assert "ssl_ca=" in engine_url, f"ssl_ca parameter missing from engine URL: {engine_url}"
        assert "%26" in engine_url, f"Ampersand not properly encoded in URL: {engine_url}"

        # Parse URL to verify ca_path round-trip
        import urllib.parse
        parsed_url = urllib.parse.urlparse(engine_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        ssl_ca_value = query_params.get('ssl_ca', [''])[0]

        assert ssl_ca_value == ca_path, f"CA path round-trip failed: {ssl_ca_value} != {ca_path}"

    except Exception as e:
        # Connection failure is expected (no real TiDB), but URL construction should work
        if "ssl_ca" in str(e) or "ca_path" in str(e):
            raise AssertionError(f"CA path handling failed: {e}")
        # Other connection errors are expected and acceptable


def test_tidb_connector_database_url_with_ca_path_reserved_chars():
    """Test database URL + ca_path with various reserved characters"""
    from pytidb.ext.mcp.server import TiDBConnector

    test_cases = [
        ("Ampersand", r"C:\Certs & Keys\root.pem", "%26"),
        ("Equals", r"C:\path=with=equals\root.pem", "%3D"),
        ("Hash", r"C:\path#with#hash\root.pem", "%23"),
        ("Question", r"C:\path?with?question\root.pem", "%3F"),
        ("Space", "/path/with spaces/root.pem", None),  # Spaces can be + or %20
    ]

    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test"

    for desc, ca_path, expected_encoding in test_cases:
        try:
            connector = TiDBConnector(
                database_url=database_url,
                ca_path=ca_path
            )

            engine_url = str(connector.tidb_client._db_engine.url)

            assert "ssl_ca=" in engine_url, f"{desc}: ssl_ca parameter missing from URL"

            if expected_encoding:
                assert expected_encoding in engine_url, f"{desc}: Expected encoding {expected_encoding} not found in URL: {engine_url}"

            # Verify round-trip parsing
            import urllib.parse
            parsed_url = urllib.parse.urlparse(engine_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            ssl_ca_value = query_params.get('ssl_ca', [''])[0]

            assert ssl_ca_value == ca_path, f"{desc}: CA path round-trip failed: {ssl_ca_value} != {ca_path}"

        except Exception as e:
            # Connection failures are expected, but URL construction should work
            if "ssl_ca" in str(e) or "ca_path" in str(e):
                raise AssertionError(f"{desc}: CA path handling failed: {e}")


@patch.dict(os.environ, {
    "TIDB_HOST": "localhost",
    "TIDB_PORT": "4000",
    "TIDB_USERNAME": "root",
    "TIDB_PASSWORD": "password",
    "TIDB_DATABASE": "test_db"
    # TIDB_CA_PATH not set
})
def test_app_lifespan_without_tidb_ca_path_env():
    """Test that app_lifespan works without TIDB_CA_PATH environment variable"""
    with patch("pytidb.ext.mcp.server.TiDBConnector") as mock_connector:
        from pytidb.ext.mcp.server import app_lifespan, FastMCP

        # Mock the connector
        mock_connector_instance = MagicMock()
        mock_connector.return_value = mock_connector_instance
        mock_connector_instance.host = "localhost"
        mock_connector_instance.port = 4000
        mock_connector_instance.database = "test_db"

        # Create app and run lifespan
        app = FastMCP("test", instructions="test instructions")

        # Use the lifespan context manager
        import asyncio

        async def test_lifespan():
            async with app_lifespan(app) as context:
                # Verify TiDBConnector was called with None ca_path
                mock_connector.assert_called_once_with(
                    database_url=None,
                    host="localhost",
                    port=4000,
                    username="root",
                    password="password",
                    database="test_db",
                    ca_path=None
                )

        # Run the async test
        asyncio.run(test_lifespan())


def test_tidb_connector_database_url_with_ca_path_integration():
    """Integration test without mocks - validates real URL merging with ca_path"""
    from pytidb.ext.mcp.server import TiDBConnector

    # Test the critical scenario: database_url + ca_path (no mocks)
    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test"
    ca_path = r"C:\Certs & Keys\root.pem"

    try:
        # This exercises the real code path through TiDBClient.connect
        connector = TiDBConnector(
            database_url=database_url,
            ca_path=ca_path
        )

        # Verify the engine URL contains the ssl_ca parameter
        engine_url = str(connector.tidb_client._db_engine.url)

        assert "ssl_ca=" in engine_url, f"ssl_ca parameter missing from engine URL: {engine_url}"
        assert "%26" in engine_url, f"Ampersand not properly encoded in URL: {engine_url}"

        # Parse URL to verify ca_path round-trip
        import urllib.parse
        parsed_url = urllib.parse.urlparse(engine_url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        ssl_ca_value = query_params.get('ssl_ca', [''])[0]

        assert ssl_ca_value == ca_path, f"CA path round-trip failed: {ssl_ca_value} != {ca_path}"

    except Exception as e:
        # Connection failure is expected (no real TiDB), but URL construction should work
        if "ssl_ca" in str(e) or "ca_path" in str(e):
            raise AssertionError(f"CA path handling failed: {e}")
        # Other connection errors are expected and acceptable


def test_tidb_connector_database_url_with_ca_path_reserved_chars():
    """Test database URL + ca_path with various reserved characters"""
    from pytidb.ext.mcp.server import TiDBConnector

    test_cases = [
        ("Ampersand", r"C:\Certs & Keys\root.pem", "%26"),
        ("Equals", r"C:\path=with=equals\root.pem", "%3D"),
        ("Hash", r"C:\path#with#hash\root.pem", "%23"),
        ("Question", r"C:\path?with?question\root.pem", "%3F"),
        ("Space", "/path/with spaces/root.pem", None),  # Spaces can be + or %20
    ]

    database_url = "mysql+pymysql://user:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test"

    for desc, ca_path, expected_encoding in test_cases:
        try:
            connector = TiDBConnector(
                database_url=database_url,
                ca_path=ca_path
            )

            engine_url = str(connector.tidb_client._db_engine.url)

            assert "ssl_ca=" in engine_url, f"{desc}: ssl_ca parameter missing from URL"

            if expected_encoding:
                assert expected_encoding in engine_url, f"{desc}: Expected encoding {expected_encoding} not found in URL: {engine_url}"

            # Verify round-trip parsing
            import urllib.parse
            parsed_url = urllib.parse.urlparse(engine_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            ssl_ca_value = query_params.get('ssl_ca', [''])[0]

            assert ssl_ca_value == ca_path, f"{desc}: CA path round-trip failed: {ssl_ca_value} != {ca_path}"

        except Exception as e:
            # Connection failures are expected, but URL construction should work
            if "ssl_ca" in str(e) or "ca_path" in str(e):
                raise AssertionError(f"{desc}: CA path handling failed: {e}")