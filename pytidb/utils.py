import re

from urllib.parse import quote
from typing import Dict, Optional, Any, List, TypeVar, Tuple

from pydantic import AnyUrl, UrlConstraints
from sqlalchemy import Column, Index, String, create_engine, make_url
from sqlmodel import AutoString
from tidb_vector.sqlalchemy import VectorType
from sqlalchemy.engine import Row
from sqlalchemy import Table
from typing import Union


TIDB_SERVERLESS_HOST_PATTERN = re.compile(
    r"gateway\d{2}\.(.+)\.(prod|dev|staging)\.(shared\.)?(aws|alicloud)\.tidbcloud\.com"
)


def create_engine_without_db(url, echo=False, **kwargs):
    temp_db_url = make_url(url)
    temp_db_url = temp_db_url._replace(database=None)
    return create_engine(temp_db_url, echo=echo, **kwargs)


class TiDBDsn(AnyUrl):
    """A type that will accept any TiDB DSN.

    * User info required
    * TLD not required
    * Host not required
    """

    _constraints = UrlConstraints(
        allowed_schemes=[
            "mysql",
            "mysql+mysqlconnector",
            "mysql+aiomysql",
            "mysql+asyncmy",
            "mysql+mysqldb",
            "mysql+pymysql",
            "mysql+cymysql",
            "mysql+pyodbc",
        ],
        default_port=4000,
        host_required=True,
    )


def build_tidb_dsn(
    schema: str = "mysql+pymysql",
    host: str = "localhost",
    port: int = 4000,
    username: str = "root",
    password: str = "",
    database: str = "test",
    enable_ssl: Optional[bool] = None,
) -> TiDBDsn:
    if enable_ssl is None:
        if host and TIDB_SERVERLESS_HOST_PATTERN.match(host):
            enable_ssl = True
        else:
            enable_ssl = None

    return TiDBDsn.build(
        scheme=schema,
        host=host,
        port=port,
        username=username,
        # TODO: remove quote after following issue is fixed:
        # https://github.com/pydantic/pydantic/issues/8061
        password=quote(password) if password else None,
        path=database,
        query="ssl_verify_cert=true&ssl_verify_identity=true" if enable_ssl else None,
    )


def filter_vector_columns(columns: Dict) -> List[Column]:
    vector_columns = []
    for column in columns:
        if isinstance(column.type, VectorType):
            vector_columns.append(column)
    return vector_columns


def check_vector_column(columns: Dict, column_name: str) -> Optional[str]:
    if column_name not in columns:
        raise ValueError(f"Non-exists vector column: {column_name}")

    vector_column = columns[column_name]
    if vector_column.type != VectorType:
        raise ValueError(f"Invalid vector column: {vector_column}")

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
    if not pk_constraint.columns:
        # Try to get _tidb_rowid if no primary key exists
        try:
            return row._mapping["_tidb_rowid"]
        except KeyError:
            return row.__hash__()

    pk_column_names = [col.name for col in pk_constraint.columns]
    try:
        if len(pk_column_names) == 1:
            return row._mapping[pk_column_names[0]]
        return tuple(row._mapping[name] for name in pk_column_names)
    except KeyError as e:
        raise KeyError(
            f"Primary key column '{e.args[0]}' not found in Row. "
            f"Available: {list(row._mapping.keys())}"
        )


def get_index_type(index: Index) -> str:
    return index.dialect_kwargs.get("mysql_prefix", "").lower()
