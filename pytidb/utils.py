import re

from urllib.parse import quote
from typing import Dict, Optional, Any, List, TypeVar, Tuple

from pydantic import AnyUrl, UrlConstraints
from sqlalchemy import Column, Index, String, create_engine, make_url
from sqlmodel import AutoString
from sqlalchemy.engine import Row
from sqlalchemy import Table
from typing import Union
from pytidb.orm.vector import VECTOR

TIDB_SERVERLESS_HOST_PATTERN = re.compile(
    r"gateway\d{2}\.(.+)\.(prod|dev|staging)\.(shared\.)?(aws|alicloud)\.tidbcloud\.com"
)


def create_engine_without_db(url, echo=False, **kwargs):
    temp_db_url = make_url(url)
    temp_db_url = temp_db_url._replace(database=None)
    return create_engine(temp_db_url, echo=echo, **kwargs)


class TiDBConnectionURL(AnyUrl):
    """A URL that enforces specific constraints for TiDB connections.

    Format:
        mysql+pymysql://[username:password@]host[:port][/database]
        mysql+pymysql://[username:password@]host[:port][/database]?ssl_verify_cert=true&ssl_verify_identity=true
    """

    _constraints = UrlConstraints(
        allowed_schemes=[
            "mysql",
            "mysql+pymysql",
        ],
        default_port=4000,
        host_required=True,
    )


def build_tidb_connection_url(
    schema: str = "mysql+pymysql",
    host: str = "localhost",
    port: int = 4000,
    username: str = "root",
    password: str = "",
    database: str = "test",
    enable_ssl: Optional[bool] = None,
) -> str:
    """
    Build a TiDB Connection URL string for database connection.

    Args:
        schema (str, optional): The connection protocol. Defaults to "mysql+pymysql".
        host (str, optional): The host address of TiDB server. Defaults to "localhost".
        port (int, optional): The port number of TiDB server. Defaults to 4000.
        username (str, optional): The username for authentication. Defaults to "root".
        password (str, optional): The password for authentication. Defaults to "".
        database (str, optional): The database name to connect to. Defaults to "test".
        enable_ssl (Optional[bool], optional): Whether to enable SSL for the connection.
            If None (default), SSL is automatically enabled for TiDB Serverless hosts
            and disabled for other hosts.

    Returns:
        str: A Connection URL string that can be used to connect to a TiDB database.
    """

    if enable_ssl is None:
        if host and TIDB_SERVERLESS_HOST_PATTERN.match(host):
            enable_ssl = True
        else:
            enable_ssl = None

    return str(
        TiDBConnectionURL.build(
            scheme=schema,
            host=host,
            port=port,
            username=username,
            # TODO: remove quote after following issue is fixed:
            # https://github.com/pydantic/pydantic/issues/8061
            password=quote(password) if password else None,
            path=database,
            query=(
                "ssl_verify_cert=true&ssl_verify_identity=true" if enable_ssl else None
            ),
        )
    )


def filter_vector_columns(columns: Dict) -> List[Column]:
    vector_columns = []
    for column in columns:
        if isinstance(column.type, VECTOR):
            vector_columns.append(column)
    return vector_columns


def check_vector_column(columns: Dict, column_name: str) -> Optional[Column]:
    if not isinstance(column_name, str):
        raise ValueError(f"Invalid vector column name: {column_name}")

    if column_name not in columns:
        raise ValueError(f"Non-exists vector column: {column_name}")

    vector_column = columns[column_name]
    if not isinstance(vector_column.type, VECTOR):
        raise ValueError(f"Invalid vector column: {column_name}")

    return vector_column


def filter_text_columns(columns: Dict) -> List[Column]:
    text_columns = []
    for column in columns:
        if isinstance(column.type, AutoString) or isinstance(column.type, String):
            text_columns.append(column)
    return text_columns


def check_text_column(columns: Dict, column_name: str) -> Optional[str]:
    if column_name not in columns:
        raise ValueError(f"Non-exists text column: {column_name}")

    text_column = columns[column_name]
    if not isinstance(text_column.type, String) and not isinstance(
        text_column.type, AutoString
    ):
        raise ValueError(f"Invalid text column: {text_column}")

    return text_column


RowKeyType = TypeVar("RowKeyType", bound=Union[Any, Tuple[Any, ...]])


def get_row_id_from_row(row: Row, table: Table) -> Optional[RowKeyType]:
    pk_constraint = table.primary_key
    pk_column_names = [col.name for col in pk_constraint.columns]
    try:
        row_mapping = (
            row._mapping
            if "_hit" not in row._mapping
            else row._mapping["_hit"].model_dump()
        )
        if len(pk_column_names) == 1:
            return row_mapping[pk_column_names[0]]
        return tuple(row_mapping[name] for name in pk_column_names)
    except KeyError as e:
        raise KeyError(
            f"Primary key column '{e.args[0]}' not found in Row. "
            f"Available: {list(row._mapping.keys())}"
        )


def get_index_type(index: Index) -> str:
    dialect_kwargs = getattr(index, "dialect_kwargs", None)
    if dialect_kwargs is None:
        return ""
    mysql_prefix = dialect_kwargs.get("mysql_prefix", "")
    return mysql_prefix.lower() if mysql_prefix else ""
