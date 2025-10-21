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

    # CA path without SSL should not include it
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

    # Relative paths should be allowed (even with traversal components)
    url = build_tidb_connection_url(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        ssl_ca_path="../certs/ca.pem"
    )
    assert "ssl_ca=..%2Fcerts%2Fca.pem" in url


def test_ensure_ssl_ca_in_url_with_prebuilt_url():
    base_url = "mysql+pymysql://root@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test"
    updated = ensure_ssl_ca_in_url(base_url, "../certs/ca.pem")
    assert "ssl_ca=..%2Fcerts%2Fca.pem" in updated
    assert "ssl_verify_cert=true" in updated
    assert "ssl_verify_identity=true" in updated

    existing_flags_url = (
        "mysql+pymysql://root@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test"
        "?ssl_verify_cert=false&ssl_verify_identity=false"
    )
    updated_existing = ensure_ssl_ca_in_url(existing_flags_url, "/path/to/ca.pem")
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in updated_existing
    # Respect existing verification flags
    assert "ssl_verify_cert=false" in updated_existing
    assert "ssl_verify_identity=false" in updated_existing

    with pytest.raises(ValueError):
        ensure_ssl_ca_in_url(base_url, "")


def test_ensure_ssl_ca_in_url_with_sqlalchemy_url_object():
    """Test that ensure_ssl_ca_in_url handles SQLAlchemy URL objects properly."""
    # Test with URL object and ssl_ca_path
    url_obj = make_url("mysql+pymysql://root:password@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test")
    updated = ensure_ssl_ca_in_url(url_obj, "/path/to/ca.pem")

    # Should return a string
    assert isinstance(updated, str)
    # Should contain password (hide_password=False)
    assert "password" in updated
    # Should contain SSL CA path
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in updated
    assert "ssl_verify_cert=true" in updated
    assert "ssl_verify_identity=true" in updated


def test_ensure_ssl_ca_in_url_with_sqlalchemy_url_object_no_ssl_ca():
    """Test that URL objects work without ssl_ca_path."""
    url_obj = make_url("mysql+pymysql://root@localhost:4000/test")
    updated = ensure_ssl_ca_in_url(url_obj, None)

    # Should return the URL as a string
    assert isinstance(updated, str)
    assert "mysql+pymysql://root@localhost:4000/test" == updated


def test_ensure_ssl_ca_in_url_with_sqlalchemy_url_object_preserves_params():
    """Test that existing query parameters in URL objects are preserved."""
    url_obj = make_url(
        "mysql+pymysql://root@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test"
        "?charset=utf8mb4&connect_timeout=10"
    )
    updated = ensure_ssl_ca_in_url(url_obj, "../certs/ca.pem")

    # Should preserve existing parameters
    assert "charset=utf8mb4" in updated
    assert "connect_timeout=10" in updated
    # Should add SSL CA parameters
    assert "ssl_ca=..%2Fcerts%2Fca.pem" in updated
    assert "ssl_verify_cert=true" in updated
    assert "ssl_verify_identity=true" in updated
