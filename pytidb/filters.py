import re
from typing import Any, Dict, List, Optional, Union

import sqlalchemy
from sqlalchemy import BinaryExpression, text

from pytidb.schema import TableModel


Filters = Union[Dict[str, Any], str, BinaryExpression]


# SQL filter operators:


def build_filter_clauses(
    filters: Filters, columns: Dict, table_model: TableModel
) -> List[BinaryExpression]:
    if isinstance(filters, dict):
        filter_clauses = build_dict_filter_clauses(filters, columns, table_model)
        return filter_clauses
    elif isinstance(filters, str):
        return [text(filters)]
    else:
        return [filters]


# Dict filter operators:

AND, OR, IN, NIN, GT, GTE, LT, LTE, EQ, NE = (
    "$and",
    "$or",
    "$in",
    "$nin",
    "$gt",
    "$gte",
    "$lt",
    "$lte",
    "$eq",
    "$ne",
)

COMPARE_OPERATOR = [IN, NIN, GT, GTE, LT, LTE, EQ, NE]

JSON_FIELD_PATTERN = re.compile(
    r"^(?P<column>[a-zA-Z_][a-zA-Z0-9_]*)\.(?P<json_field>[a-zA-Z_][a-zA-Z0-9_]*)$"
)


def build_dict_filter_clauses(
    filters: Dict[str, Any] | None, columns: Dict, table_model: TableModel
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
                filter_clause = build_dict_column_filter(column, value)
            else:
                # implicit $eq operator: value maybe int / float / string
                filter_clause = build_dict_column_filter(column, {EQ: value})
            if filter_clause is not None:
                filter_clauses.append(filter_clause)
        elif "." in key:
            match = JSON_FIELD_PATTERN.match(key)
            if not match:
                raise ValueError(
                    f"Got unexpected filter key: {key}, please use valid column name instead"
                )
            column_name = match.group("column")
            json_field = match.group("json_field")
            column = sqlalchemy.func.json_extract(
                getattr(table_model, column_name), f"$.{json_field}"
            )
            if isinstance(value, dict):
                filter_clause = build_dict_column_filter(column, value)
            else:
                # implicit $eq operator: value maybe int / float / string
                filter_clause = build_dict_column_filter(column, {EQ: value})
            if filter_clause is not None:
                filter_clauses.append(filter_clause)
        else:
            raise ValueError(
                f"Got unexpected filter key: {key}, please use valid column name instead"
            )

    return filter_clauses


def build_dict_column_filter(
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
