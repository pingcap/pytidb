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
    # Test CA path with TiDB Serverless (SSL auto-enabled)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path="/path/to/ca-cert.pem",
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=/path/to/ca-cert.pem"
    )

    # Test CA path with SSL explicitly enabled
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        enable_ssl=True,
        ca_path="/path/to/ca-cert.pem",
    )
    assert (
        url
        == "mysql+pymysql://root:password@localhost:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=/path/to/ca-cert.pem"
    )

    # Test CA path with SSL disabled (should not include ca_path)
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        enable_ssl=False,
        ca_path="/path/to/ca-cert.pem",
    )
    assert url == "mysql+pymysql://root:password@localhost:4000/test"

    # Test CA path with special characters (URL encoding)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path="/path/to/ca file with spaces.pem",
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=%2Fpath%2Fto%2Fca%20file%20with%20spaces.pem"
    )


def test_build_tidb_conn_url_ca_path_edge_cases():
    # Test empty CA path (should be ignored)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path="",
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )

    # Test None CA path (should be ignored)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path=None,
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )

    # Test CA path with local TiDB (SSL disabled by default)
    url = build_tidb_connection_url(
        host="localhost",
        username="root",
        password="password",
        ca_path="/path/to/ca-cert.pem",
    )
    assert url == "mysql+pymysql://root:password@localhost:4000/test"


def test_build_tidb_conn_url_ca_path_reserved_characters():
    """Test CA path with reserved URL characters are properly encoded"""

    # Test Windows path with ampersand - Critical issue fix
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path=r"C:\Certs & Keys\root.pem",
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=C%3A%5CCerts%20%26%20Keys%5Croot.pem"
    )

    # Test path with equals sign
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path=r"C:\path=with=equals\root.pem",
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=C%3A%5Cpath%3Dwith%3Dequals%5Croot.pem"
    )

    # Test path with multiple reserved characters (& = # ? : \)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path=r"C:\path with space&ampersand=equals#hash?query.pem",
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=C%3A%5Cpath%20with%20space%26ampersand%3Dequals%23hash%3Fquery.pem"
    )

    # Test Unix path with reserved characters
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user.root",
        password="pass",
        ca_path="/path/with space&ampersand=equals#hash?query.pem",
    )
    assert (
        url
        == "mysql+pymysql://user.root:pass@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true&ssl_ca=%2Fpath%2Fwith%20space%26ampersand%3Dequals%23hash%3Fquery.pem"
    )


def test_build_tidb_conn_url_invalid():
    # Unacceptable schema
    with pytest.raises(ValueError):
        build_tidb_connection_url(schema="invalid_schema")

    # Missing host
    with pytest.raises(ValueError):
        build_tidb_connection_url(host="")
