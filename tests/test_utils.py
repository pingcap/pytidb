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


def test_build_tidb_conn_url_invalid():
    # Unacceptable schema
    with pytest.raises(ValueError):
        build_tidb_connection_url(schema="invalid_schema")

    # Missing host
    with pytest.raises(ValueError):
        build_tidb_connection_url(host="")


def test_build_tidb_conn_url_with_ssl_ca():
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


def test_build_tidb_conn_url_with_ssl_ca_serverless():
    # For TiDB Serverless with ssl_ca
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
        ssl_ca="/path/to/ca.pem",
    )
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in url
    assert "ssl_verify_cert=true" in url
    assert "ssl_verify_identity=true" in url
    # Verify the URL can be created without database connection
    assert url.startswith("mysql+pymysql://")
