import math
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from sqlalchemy import result_tuple
from sqlalchemy.engine import Row


from pytidb.utils import RowKeyType
from pytidb.schema import DistanceMetric


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


def fusion_result_rows_by_weighted(
    vs_rows: List[Row],
    fts_rows: List[Row],
    get_row_key: Callable[[Row], RowKeyType],
    vs_metric: DistanceMetric,
    vs_weight: float = 0.5,
    fts_weight: float = 0.5,
) -> Tuple[List[str], List[Row]]:
    """
    Fusion the search results by weights.

    Args:
        vs_rows: Vector search list of result rows
        fts_rows: Full text search list of result rows
        get_row_key: Function to get the key (primary key or _tidb_rowid) from a row
        vs_metric: The metric type of vector search.
        vs_weight: The weight of the vector search results. Must be a number between 0 and 1. Default is 0.5.
        fts_weight: The weight of the full text search results. Must be a number between 0 and 1. Default is 0.5.
    Returns:
        Tuple containing:
        - List of field names
        - List of fused result rows sorted by RRF score
    """
    if not vs_rows and not fts_rows:
        return [], []

    if vs_weight <= 0 or vs_weight >= 1 or fts_weight <= 0 or fts_weight >= 1:
        raise ValueError("weight must be a number between 0 and 1")
    if vs_weight + fts_weight == 0:
        raise ValueError("At least one weight must be greater than 0")

    # Calculate weighted scores for each result in both lists
    weighted_scores = {}

    # Process first list
    for i, row in enumerate(vs_rows):
        vs_distance = row._mapping["_distance"]

        if vs_metric == DistanceMetric.COSINE:
            normalized_vs_distance = _normalize_score(vs_distance, "cosine")
        elif vs_metric == DistanceMetric.L2:
            normalized_vs_distance = _normalize_score(vs_distance, "l2")
        else:
            raise ValueError("Invalid distance metric")

        key = get_row_key(row)
        weighted_scores[key] = normalized_vs_distance * vs_weight

    # Process second list and add scores
    for i, row in enumerate(fts_rows):
        match_score = row._mapping["_match_score"]
        normalized_match_score = _normalize_score(match_score, "bm25")
        key = get_row_key(row)
        if key in weighted_scores:
            weighted_scores[key] += normalized_match_score * fts_weight
        else:
            weighted_scores[key] = normalized_match_score * fts_weight

    # Merge rows.
    fusion_strategies = {
        "_score": lambda a, b, row_a, row_b, key: weighted_scores[key],
    }
    all_fields, merged_rows = merge_result_rows(
        vs_rows, fts_rows, get_row_key, fusion_strategies
    )

    # Sort rows by weighted score.
    sorted_rows = sorted(
        merged_rows, key=lambda row: row._mapping["_score"] or 0, reverse=True
    )

    return all_fields, sorted_rows


def _normalize_score(
    score: float, metric_type: Literal["l2", "cosine", "bm25"]
) -> float:
    """Normalize the score to [0, 1] range and ensure that the higher normalized values
    correspond to greater similarity.

    Args:
        score: The score to normalize.
        metric_type: The metric type of score.

    Returns:
        The normalized score between 0 and 1.
    """

    if metric_type == "cosine":
        # Cosine distance range is [0, 2] and smaller values indicate higher
        # similarity (need inverted).
        return 1.0 - (score / 2.0)
    elif metric_type == "l2":
        # L2 distance range is [0, +infinity) and smaller values indicate higher
        # similarity (need inverted).
        return 1.0 - (2.0 * math.atan(score) / math.pi)
    elif metric_type == "bm25":
        # BM25 score range is [0, +infinity) and larger values indicate higher
        # match degree (no need to invert).
        return 2.0 * math.atan(score) / math.pi
    else:
        raise ValueError(f"Invalid metric type for score normalization: {metric_type}")
