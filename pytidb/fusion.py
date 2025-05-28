from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import result_tuple
from sqlalchemy.engine import Row

from pytidb.utils import RowKeyType


FusionFunction = Callable[[Any, Any, Row, Row, Optional[RowKeyType]], Any]


def merge_result_rows(
    rows_a: List[Row],
    rows_b: List[Row],
    get_row_key: Callable[[Row], RowKeyType],
    fusion_strategies: Optional[Dict[str, FusionFunction]] = None,
) -> Tuple[List[str], List[Row]]:
    """Merge two lists of result rows based on row_id.

    Args:
        rows_a: First list of result rows
        rows_b: Second list of result rows
        get_row_key: Function to get the key (primary key or _tidb_rowid) from a row
        fusion_strategies: Optional dictionary mapping field names to custom fusion functions.
                   Each fusion function takes (value_a, value_b, row_a, row_b, key) as arguments
                   and returns the fused value. If both rows_a and rows_b are empty,
                   fusion_strategies will not be used.

    Returns:
        Tuple containing:
        - List of all field names from both input rows
        - List of merged result rows
    """
    if not rows_a and not rows_b:
        return [], []

    # Get all column names
    fields_a = list(rows_a[0]._fields) if len(rows_a) > 0 else []
    fields_b = list(rows_b[0]._fields) if len(rows_b) > 0 else []
    all_fields = list(dict.fromkeys(fields_a + fields_b).keys())

    # Create a mapping of keys to rows from both lists
    rows_by_key_a = {get_row_key(row): row for row in rows_a}
    rows_by_key_b = {get_row_key(row): row for row in rows_b}

    # Get all unique keys.
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
            if fusion_strategies and field in fusion_strategies:
                value = fusion_strategies[field](value_a, value_b, row_a, row_b, key)
            else:
                # Default strategy: use value_a if not None, otherwise use value_b
                value = value_a if value_a is not None else value_b

            row_data.append(value)

        # Create new Row object using result_tuple
        row_factory = result_tuple(all_fields)
        merged_row = row_factory(row_data)
        merged_rows.append(merged_row)

    return all_fields, merged_rows


def fusion_result_rows_by_rrf(
    rows_a: List[Row],
    rows_b: List[Row],
    get_row_key: Callable[[Row], RowKeyType],
    k: Optional[int] = 60,
) -> Tuple[List[str], List[Row]]:
    """
    Fusion the search results by RRF (Reciprocal Rank Fusion).

    Args:
        rows_a: First list of result rows
        rows_b: Second list of result rows
        get_row_key: Function to get the key (primary key or _tidb_rowid) from a row
        k: The constant used in RRF formula. Must be a positive number. Default is 60.

    Returns:
        Tuple containing:
        - List of field names
        - List of fused result rows sorted by RRF score
    """
    if not rows_a and not rows_b:
        return [], []

    if k <= 0:
        raise ValueError("k must be a positive number")

    # Calculate RRF scores for each result in both lists
    rrf_scores = {}

    # Process first list
    for i, row in enumerate(rows_a):
        rank = i + 1
        key = get_row_key(row)
        rrf_scores[key] = 1.0 / (k + rank)

    # Process second list and add scores
    for i, row in enumerate(rows_b):
        rank = i + 1
        key = get_row_key(row)
        if key in rrf_scores:
            rrf_scores[key] += 1.0 / (k + rank)
        else:
            rrf_scores[key] = 1.0 / (k + rank)

    # Merge rows.
    fusion_strategies = {
        "_score": lambda a, b, row_a, row_b, key: rrf_scores[key],
    }
    all_fields, merged_rows = merge_result_rows(
        rows_a, rows_b, get_row_key, fusion_strategies
    )

    # Sort rows by RRF score.
    sorted_rows = sorted(
        merged_rows, key=lambda row: row._mapping["_score"] or 0, reverse=True
    )

    return all_fields, sorted_rows
