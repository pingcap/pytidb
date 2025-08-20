import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import sqlalchemy
from sqlalchemy import BinaryExpression, ColumnElement, text, FromClause

if TYPE_CHECKING:
    pass


Filters = Union[Dict[str, Any], str, ColumnElement[bool]]


# SQL filter operators:


def build_filter_clauses(
    filters: Filters, target_table: FromClause, post_filter: bool = False
) -> List[BinaryExpression]:
    """
    Build filter clauses for the given filters.

    Args:
        filters: The filters to apply
        target_table: The table or subquery to apply filters to.
        post_filter: If True, convert BinaryExpression filters to reference subquery columns.
                    When True, target_table should be a subquery.

    Returns:
        List of SQLAlchemy filter expressions
    """
    if isinstance(filters, dict):
        return build_dict_filter_clauses(filters, target_table)
    elif isinstance(filters, str):
        return [text(filters)]
    elif isinstance(filters, ColumnElement):
        return build_python_filter_clauses(filters, target_table, post_filter)
    else:
        raise ValueError(f"Unsupported filters: {type(filters)}")


# Dictionary-like filter:


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
    filters: Dict[str, Any] | None,
    target_table: FromClause,
) -> List[BinaryExpression]:
    if filters is None:
        return []

    filter_clauses = []
    columns = target_table.c

    for key, value in filters.items():
        if key.lower() == AND:
            if not isinstance(value, list):
                raise TypeError(
                    f"Expect a list value for $and operator, but got {type(value)}"
                )
            and_clauses = []
            for item in value:
                and_clauses.extend(build_dict_filter_clauses(item, target_table))
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
                or_clauses.extend(build_dict_filter_clauses(item, target_table))
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
                getattr(columns, column_name), f"$.{json_field}"
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


# Python-expression filter:


def build_python_filter_clauses(
    filters: ColumnElement[bool], target_table: FromClause, post_filter: bool = False
) -> List[BinaryExpression]:
    """
    Build filter clauses for Python expression filters.

    Args:
        filters: The Python expression filter to apply
        target_table: The table or subquery to apply filters to
        post_filter: If True, convert filters to reference subquery columns

    Returns:
        List of SQLAlchemy filter expressions
    """
    if not post_filter:
        return [filters]

    # Handle BinaryExpression filters
    if isinstance(filters, BinaryExpression):
        return [make_filters_apply_to_subquery(filters, target_table)]
    elif hasattr(filters, "clauses"):
        # Handle complex expressions like AND/OR operations
        return [make_complex_expression_apply_to_subquery(filters, target_table)]
    else:
        # For other types, return unchanged
        return [filters]


def make_filters_apply_to_subquery(
    binary_expr: BinaryExpression, subquery: FromClause
) -> BinaryExpression:
    """
    Convert a BinaryExpression that references table columns to reference subquery columns.

    Args:
        binary_expr: The BinaryExpression to convert
        subquery: The subquery to reference columns from

    Returns:
        Converted BinaryExpression referencing subquery columns
    """
    from sqlalchemy import Column

    def convert_column_ref(expr):
        if isinstance(expr, Column):
            # Get the column name from the original column
            column_name = expr.name
            # Reference the same column from the subquery
            return getattr(subquery.c, column_name)
        elif hasattr(expr, "left") and hasattr(expr, "right"):
            # Handle nested expressions (like JSON operations)
            left = convert_column_ref(expr.left)
            right = convert_column_ref(expr.right)
            # Recreate the expression with converted operands
            if hasattr(expr, "op"):
                # Call the operator function to get the actual expression
                return expr.op(left, right)
            else:
                # For simple comparisons, try to recreate the expression
                return type(expr)(left, right)
        else:
            # Return unchanged for non-column references (literals, etc.)
            return expr

    # Convert both left and right sides of the binary expression
    left = convert_column_ref(binary_expr.left)
    right = convert_column_ref(binary_expr.right)

    # Recreate the binary expression with converted operands
    # For SQLAlchemy binary expressions, we need to use the operator directly
    if hasattr(binary_expr, "operator"):
        # Use the operator attribute to recreate the expression
        # The operator might be a function object, so we need to check differently
        if (
            binary_expr.operator.__name__ == "eq"
            or str(binary_expr.operator) == "<built-in function eq>"
        ):
            return left == right
        elif (
            binary_expr.operator.__name__ == "ne"
            or str(binary_expr.operator) == "<built-in function ne>"
        ):
            return left != right
        elif (
            binary_expr.operator.__name__ == "gt"
            or str(binary_expr.operator) == "<built-in function gt>"
        ):
            return left > right
        elif (
            binary_expr.operator.__name__ == "ge"
            or str(binary_expr.operator) == "<built-in function ge>"
        ):
            return left >= right
        elif (
            binary_expr.operator.__name__ == "lt"
            or str(binary_expr.operator) == "<built-in function lt>"
        ):
            return left < right
        elif (
            binary_expr.operator.__name__ == "le"
            or str(binary_expr.operator) == "<built-in function le>"
        ):
            return left <= right
        elif (
            binary_expr.operator.__name__ == "in"
            or str(binary_expr.operator) == "<built-in function in>"
            or "in_op" in str(binary_expr.operator)
        ):
            return left.in_(right)
        elif (
            binary_expr.operator.__name__ == "notin"
            or str(binary_expr.operator) == "<built-in function notin>"
            or "notin_op" in str(binary_expr.operator)
        ):
            return ~left.in_(right)
        else:
            # For other operators, we can't easily recreate them
            # This should not happen with standard SQLAlchemy operators
            raise ValueError(f"Unsupported operator: {binary_expr.operator}")
    else:
        # If no operator attribute, we can't recreate the expression
        raise ValueError("BinaryExpression has no operator attribute, cannot convert")


def make_complex_expression_apply_to_subquery(
    complex_expr: Any, subquery: FromClause
) -> Any:
    """
    Convert a complex expression (like AND/OR operations) to reference subquery columns.

    Args:
        complex_expr: The complex expression to convert
        subquery: The subquery to reference columns from

    Returns:
        Converted complex expression referencing subquery columns
    """
    # These have a .clauses attribute that contains the individual expressions
    converted_clauses = []
    for clause in complex_expr.clauses:
        if isinstance(clause, BinaryExpression):
            converted_clauses.append(make_filters_apply_to_subquery(clause, subquery))
        else:
            # For other types, try to convert recursively
            converted_clauses.extend(
                build_python_filter_clauses(clause, subquery, post_filter=True)
            )

    # Recreate the complex expression with converted clauses
    # Use the appropriate SQLAlchemy functions instead of trying to recreate the class
    if len(converted_clauses) == 1:
        return converted_clauses[0]
    elif hasattr(complex_expr, "__class__"):
        class_name = complex_expr.__class__.__name__
        if "And" in class_name or "and" in str(complex_expr).lower():
            return sqlalchemy.and_(*converted_clauses)
        elif "Or" in class_name or "or" in str(complex_expr).lower():
            return sqlalchemy.or_(*converted_clauses)
        else:
            # Fallback: return individual clauses
            return converted_clauses
    else:
        return converted_clauses
