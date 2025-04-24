import re

from urllib.parse import quote
from typing import Dict, Optional, Any, List, Callable, TypeVar, Tuple

import sqlalchemy
from pydantic import AnyUrl, UrlConstraints
from sqlalchemy import BinaryExpression, Column, String
from sqlmodel import AutoString
from tidb_vector.sqlalchemy import VectorType
from sqlalchemy.engine import Row
from sqlalchemy.engine.result import result_tuple
from sqlalchemy import Table
from typing import Union

from pytidb.schema import TableModel
from pytidb.constants import (
    AND,
    OR,
    EQ,
    IN,
    NIN,
    GT,
    GTE,
    LT,
    LTE,
    NE,
)

JSON_FIELD_PATTERN = re.compile(
    r"^(?P<column>[a-zA-Z_][a-zA-Z0-9_]*)\.(?P<json_field>[a-zA-Z_][a-zA-Z0-9_]*)$"
)


TIDB_SERVERLESS_HOST_PATTERN = re.compile(
    r"gateway\d{2}\.(.+)\.(prod|dev|staging)\.(shared\.)?(aws|alicloud)\.tidbcloud\.com"
)


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


def build_filter_clauses(
    filters: Dict[str, Any], columns: Dict, table_model: TableModel
) -> List[BinaryExpression]:
    if filters is None:
        return []

    filter_clauses = []
    for key, value in filters.items():
        if key.lower() == AND:
            if not isinstance(value, list):
                raise TypeError(
                    f"Expect a list value for $and operator, but got {type(value)}"
                )
            and_clauses = []
            for item in value:
                and_clauses.extend(build_filter_clauses(item, columns, table_model))
            if len(and_clauses) == 0:
                continue
            filter_clauses.append(sqlalchemy.and_(*and_clauses))
        elif key.lower() == OR:
            if not isinstance(value, list):
                raise TypeError(
                    f"Expect a list value for $or operator, but got {type(value)}"
                )
            or_clauses = []
            for item in value:
                or_clauses.extend(build_filter_clauses(item, columns, table_model))
            if len(or_clauses) == 0:
                continue
            filter_clauses.append(sqlalchemy.or_(*or_clauses))
        elif key in columns:
            column = getattr(columns, key)
            if isinstance(value, dict):
                filter_clause = build_column_filter(column, value)
            else:
                # value maybe int / float / string
                filter_clause = build_column_filter(column, {EQ: value})
            if filter_clause is not None:
                filter_clauses.append(filter_clause)
        elif "." in key:
            match = JSON_FIELD_PATTERN.match(key)
            if match:
                column = match.group("column")
                json_field = match.group("json_field")
                column = sqlalchemy.func.json_extract(
                    getattr(table_model, column), f"$.{json_field}"
                )
                filter_clause = build_column_filter(column, value)
                if filter_clause is not None:
                    filter_clauses.append(filter_clause)
        else:
            raise ValueError(
                f"Got unexpected filter key: {key}, please use valid column name instead"
            )

    return filter_clauses


def build_column_filter(
    column: Any, conditions: Dict[str, Any]
) -> Optional[BinaryExpression]:
    column_filters = []
    for operator, val in conditions.items():
        op = operator.lower()
        if op == IN:
            column_filters.append(column.in_(val))
        elif op == NIN:
            column_filters.append(~column.in_(val))
        elif op == GT:
            column_filters.append(column > val)
        elif op == GTE:
            column_filters.append(column >= val)
        elif op == LT:
            column_filters.append(column < val)
        elif op == LTE:
            column_filters.append(column <= val)
        elif op == NE:
            column_filters.append(column != val)
        elif op == EQ:
            column_filters.append(column == val)
        else:
            raise ValueError(
                f"Unknown filter operator {operator}. Consider using "
                "one of $in, $nin, $gt, $gte, $lt, $lte, $eq, $ne."
            )
    if len(column_filters) == 0:
        return None
    elif len(column_filters) == 1:
        return column_filters[0]
    else:
        return sqlalchemy.and_(*column_filters)


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


def merge_result_rows(
    rows_a: List[Row],
    rows_b: List[Row],
    get_row_key: Callable[[Row], RowKeyType],
    merge_strategies: Optional[Dict[str, Callable[[Any, Any, Row, Row], Any]]] = None,
) -> Tuple[List[str], List[Row]]:
    """Merge two lists of result rows based on row_id.

    Args:
        rows_a: First list of result rows
        rows_b: Second list of result rows
        get_row_key: Function to get the key (primary key or _tidb_rowid) from a row
        merge_strategies: Optional dictionary mapping field names to custom merge functions.
                   Each merge function takes (value_a, value_b, row_a, row_b) as arguments
                   and returns the merged value.

    Returns:
        List of merged result rows
    """
    if not rows_a and not rows_b:
        return [], []
    if not rows_a or len(rows_a) == 0:
        return list(rows_b[0]._fields), rows_b
    if not rows_b or len(rows_b) == 0:
        return list(rows_a[0]._fields), rows_a

    # Get all column names
    fields_a = list(rows_a[0]._fields)
    fields_b = list(rows_b[0]._fields)
    all_fields = list(dict.fromkeys(fields_a + fields_b).keys())

    # Build mapping from key to row data
    rows_by_key_a = {get_row_key(row): row for row in rows_a}
    rows_by_key_b = {get_row_key(row): row for row in rows_b}

    # Get all unique keys
    all_keys = set(rows_by_key_a.keys()) | set(rows_by_key_b.keys())

    # Merge results
    merged_rows = []
    for key in all_keys:
        row_data = []
        row_a = rows_by_key_a.get(key)
        row_b = rows_by_key_b.get(key)

        for field in all_fields:
            value_a = getattr(row_a, field) if row_a and field in fields_a else None
            value_b = getattr(row_b, field) if row_b and field in fields_b else None

            # Use custom merge strategy if provided
            if merge_strategies and field in merge_strategies:
                value = merge_strategies[field](value_a, value_b, row_a, row_b)
            else:
                # Default strategy: use value_a if not None, otherwise use value_b
                value = value_a if value_a is not None else value_b

            row_data.append(value)

        # Create new Row object using result_tuple
        row_factory = result_tuple(all_fields)
        merged_row = row_factory(row_data)
        merged_rows.append(merged_row)

    return all_fields, merged_rows
