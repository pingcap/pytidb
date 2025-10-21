from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import make_url

from pytidb.client import TiDBClient


@patch("pytidb.client.create_engine")
def test_connect_honors_ssl_ca_for_prebuilt_url(mock_create_engine):
    mock_engine = MagicMock()
    mock_engine.dialect.identifier_preparer = MagicMock()
    mock_engine.url = SimpleNamespace(host="gateway01.us-west-2.prod.aws.tidbcloud.com")
    mock_create_engine.return_value = mock_engine

    TiDBClient.connect(
        url="mysql+pymysql://root@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?foo=bar",
        ssl_ca_path="../certs/ca.pem",
        host=None,
    )

    passed_url = mock_create_engine.call_args[0][0]
    assert "foo=bar" in passed_url
    assert "ssl_ca=..%2Fcerts%2Fca.pem" in passed_url
    assert "ssl_verify_cert=true" in passed_url
    assert "ssl_verify_identity=true" in passed_url


@patch("pytidb.client.create_engine")
def test_connect_invalid_ssl_ca_for_prebuilt_url(mock_create_engine):
    with pytest.raises(ValueError):
        TiDBClient.connect(
            url="mysql+pymysql://root@localhost:4000/test",
            ssl_ca_path="",
            host=None,
        )

    mock_create_engine.assert_not_called()


@patch("pytidb.client.create_engine")
def test_connect_with_sqlalchemy_url_object_and_ssl_ca(mock_create_engine):
    """Test that SQLAlchemy URL objects are properly handled with ssl_ca_path."""
    mock_engine = MagicMock()
    mock_engine.dialect.identifier_preparer = MagicMock()
    mock_engine.url = SimpleNamespace(host="gateway01.us-west-2.prod.aws.tidbcloud.com")
    mock_create_engine.return_value = mock_engine

    # Create a SQLAlchemy URL object
    url_obj = make_url("mysql+pymysql://root:password@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test")

    TiDBClient.connect(
        url=url_obj,
        ssl_ca_path="/path/to/ca.pem",
        host=None,
    )

    passed_url = mock_create_engine.call_args[0][0]
    # Should contain password from URL object
    assert "password" in passed_url
    # Should contain SSL CA path
    assert "ssl_ca=%2Fpath%2Fto%2Fca.pem" in passed_url
    assert "ssl_verify_cert=true" in passed_url
    assert "ssl_verify_identity=true" in passed_url


@patch("pytidb.client.create_engine")
def test_connect_with_sqlalchemy_url_object_without_ssl_ca(mock_create_engine):
    """Test that SQLAlchemy URL objects work without ssl_ca_path."""
    mock_engine = MagicMock()
    mock_engine.dialect.identifier_preparer = MagicMock()
    mock_engine.url = SimpleNamespace(host="localhost")
    mock_create_engine.return_value = mock_engine

    # Create a SQLAlchemy URL object
    url_obj = make_url("mysql+pymysql://root@localhost:4000/test")

    TiDBClient.connect(url=url_obj, host=None)

    passed_url = mock_create_engine.call_args[0][0]
    # Should be a valid URL string
    assert "mysql+pymysql://root@localhost:4000/test" == passed_url


@patch("pytidb.client.create_engine")
def test_connect_with_sqlalchemy_url_object_preserves_existing_params(mock_create_engine):
    """Test that existing URL parameters are preserved when using URL objects."""
    mock_engine = MagicMock()
    mock_engine.dialect.identifier_preparer = MagicMock()
    mock_engine.url = SimpleNamespace(host="gateway01.us-west-2.prod.aws.tidbcloud.com")
    mock_create_engine.return_value = mock_engine

    # Create a SQLAlchemy URL object with existing query parameters
    url_obj = make_url("mysql+pymysql://root@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?charset=utf8mb4")

    TiDBClient.connect(
        url=url_obj,
        ssl_ca_path="../certs/ca.pem",
        host=None,
    )

    passed_url = mock_create_engine.call_args[0][0]
    # Should preserve existing charset parameter
    assert "charset=utf8mb4" in passed_url
    # Should add SSL CA path
    assert "ssl_ca=..%2Fcerts%2Fca.pem" in passed_url
    assert "ssl_verify_cert=true" in passed_url
    assert "ssl_verify_identity=true" in passed_url
