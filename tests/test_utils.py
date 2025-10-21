import pytest
from sqlalchemy import make_url

from pytidb.utils import build_tidb_connection_url, ensure_ssl_ca_in_url


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
    # For TiDB Serverless with custom CA path
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
        ssl_ca_path="/path/to/ca-cert.pem",
    )
    assert (
        url
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=%2Fpath%2Fto%2Fca-cert.pem"
    )

    # For local TiDB with explicit SSL and CA path
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        enable_ssl=True,
        ssl_ca_path="/custom/ca.pem",
    )
    assert (
        url
        == "mysql+pymysql://root:password@localhost:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=%2Fcustom%2Fca.pem"
    )

    # For dedicated TiDB cluster with ssl_ca_path only (P0 fix)
    # This is the critical case: dedicated cluster (non-serverless hostname)
    # with ssl_ca_path but no explicit enable_ssl - should auto-enable SSL
    url = build_tidb_connection_url(
        host="tidb-dedicated.xyz.prod.aws.tidbcloud.com",
        username="root",
        password="password",
        ssl_ca_path="/path/to/ca.pem",
    )
    assert "ssl_verify_cert=true" in url
    assert "ssl_verify_identity=true" in url
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in url

    # CA path with explicit disable_ssl should not include SSL params
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        enable_ssl=False,
        ssl_ca_path="/path/to/ca.pem",
    )
    assert url == "mysql+pymysql://root:password@localhost:4000/test"


def test_build_tidb_conn_url_invalid():
    # Unacceptable schema
    with pytest.raises(ValueError):
        build_tidb_connection_url(schema="invalid_schema")

    # Missing host
    with pytest.raises(ValueError):
        build_tidb_connection_url(host="")


def test_build_tidb_conn_url_ca_path_security():
    # Test security validation for CA path
    with pytest.raises(ValueError, match="ssl_ca_path must be a non-empty string"):
        build_tidb_connection_url(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            ssl_ca_path=""
        )

    with pytest.raises(ValueError, match="Invalid ssl_ca_path: potential security risk"):
        build_tidb_connection_url(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            ssl_ca_path="../../../etc/passwd"
        )

    with pytest.raises(ValueError, match="Invalid ssl_ca_path: potential security risk"):
        build_tidb_connection_url(
            host="gateway01.us-west-2.prod.aws.tidbcloud.com",
            ssl_ca_path="/dev/null"
        )
