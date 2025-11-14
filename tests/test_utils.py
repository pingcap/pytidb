import pytest
from pytidb.utils import build_tidb_connection_url


def test_build_tidb_conn_url():
    # For TiDB Serverless
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
    )
    assert (
        url
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )

    # For TiDB Cluster on local.
    url = build_tidb_connection_url(
        host="localhost", username="root", password="password"
    )
    assert url == "mysql+pymysql://root:password@localhost:4000/test"

    # Defaults
    url = build_tidb_connection_url()
    assert url == "mysql+pymysql://root@localhost:4000/test"


def test_build_tidb_conn_url_with_ca_path():
    """Test that ca_path parameter is correctly added to connection URL."""
    # For TiDB Serverless with CA path (SSL enabled)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
        ca_path="/path/to/ca.pem"
    )
    assert (
        url
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=%2Fpath%2Fto%2Fca.pem"
    )

    # For TiDB Serverless with CA path containing special characters
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
        ca_path="/path with spaces/ca.pem"
    )
    assert "ssl_ca=%2Fpath%20with%20spaces%2Fca.pem" in url


def test_build_tidb_conn_url_with_ca_path_non_serverless():
    """Test that ca_path is only added when SSL is enabled."""
    # For regular TiDB (not Serverless) with CA path explicitly enabled
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        ca_path="/path/to/ca.pem",
        enable_ssl=True
    )
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in url


def test_build_tidb_conn_url_ca_path_without_ssl():
    """Test that ca_path is ignored when SSL is not enabled."""
    # For regular TiDB without SSL
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        ca_path="/path/to/ca.pem",
        enable_ssl=False
    )
    assert "ssl_ca" not in url
    assert "?" not in url


def test_build_tidb_conn_url_backward_compatibility():
    """Test that existing behavior is unchanged without ca_path parameter."""
    # Without ca_path, should work exactly as before
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
    )
    assert (
        url
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )
    assert "ssl_ca" not in url


def test_build_tidb_conn_url_invalid():
    # Unacceptable schema
    with pytest.raises(ValueError):
        build_tidb_connection_url(schema="invalid_schema")

    # Missing host
    with pytest.raises(ValueError):
        build_tidb_connection_url(host="")
