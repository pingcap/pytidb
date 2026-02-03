import pytest
from sqlalchemy.engine.result import SimpleResultMetaData
from sqlalchemy.engine.row import Row

from pytidb.utils import build_tidb_connection_url


def normalize_sql(sql: str) -> str:
    """Collapse all whitespace to single space for stable comparison.
    Also remove space after '(' and before ')' to match compiler output.
    """
    s = " ".join(sql.split())
    s = s.replace(" ( ", " (").replace(" (", "(")
    s = s.replace(" ) ", ") ")
    return s


def create_row_from_dict(data: dict) -> Row:
    """Create a Row object from a dictionary.

    Args:
        data: A dictionary containing the row data

    Returns:
        A Row object with the data from the dictionary
    """
    # Create metadata with column names from dict keys
    metadata = SimpleResultMetaData(tuple(data.keys()))

    # Create Row object with metadata and values
    row = Row(
        metadata,
        None,  # processors
        metadata._key_to_index,
        tuple(data.values()),
    )

    return row


def create_rows_from_list(data: list[dict]) -> list[Row]:
    """Create a list of Row objects from a list of dictionaries.

    Args:
        data: A list of dictionaries containing the row data

    Returns:
        A list of Row objects with the data from the dictionaries
    """
    return [create_row_from_dict(row) for row in data]


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
