from typing import List, Dict
import pytest
from sqlalchemy import Row

from pytidb.fusion import fusion_result_rows_by_rrf, fusion_result_rows_by_weighted
from tests.utils import create_rows_from_list


# Test cases for RRF fusion.


class RRFFusionTestCase:
    def __init__(
        self,
        name: str,
        vs_rows: List[Dict],
        fts_rows: List[Dict],
        expected: List[Dict],
    ):
        self.name = name
        self.vs_rows = vs_rows
        self.fts_rows = fts_rows
        self.expected = expected


def get_row_id(row: Row):
    return row.id


RRF_TEST_CASES = [
    RRFFusionTestCase(
        name="fts_rows_and_vs_rows",
        vs_rows=[
            {"id": 101, "_distance": 0.1, "_match_score": None, "_score": 0.9},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.8},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.7},
            {"id": 198, "_distance": 0.4, "_match_score": None, "_score": 0.6},
            {"id": 175, "_distance": 0.5, "_match_score": None, "_score": 0.5},
        ],
        fts_rows=[
            {"id": 198, "_distance": None, "_match_score": 2.5, "_score": 2.5},
            {"id": 101, "_distance": None, "_match_score": 2.4, "_score": 2.4},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 2.3},
            {"id": 175, "_distance": None, "_match_score": 2.2, "_score": 2.2},
            {"id": 250, "_distance": None, "_match_score": 2.1, "_score": 2.1},
        ],
        expected=[
            {"id": 101, "_distance": 0.1, "_match_score": 2.4, "_score": 0.03252},
            {"id": 198, "_distance": 0.4, "_match_score": 2.5, "_score": 0.03202},
            {"id": 175, "_distance": 0.5, "_match_score": 2.2, "_score": 0.03101},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.01613},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 0.01587},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.01587},
            {"id": 250, "_distance": None, "_match_score": 2.1, "_score": 0.01538},
        ],
    ),
    RRFFusionTestCase(
        name="empty_fts_rows",
        vs_rows=[
            {"id": 101, "_distance": 0.1, "_match_score": None, "_score": 0.9},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.8},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.7},
        ],
        fts_rows=[],
        expected=[
            {"id": 101, "_distance": 0.1, "_match_score": None, "_score": 0.01639},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.01613},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.01587},
        ],
    ),
    RRFFusionTestCase(
        name="empty_vs_rows",
        vs_rows=[],
        fts_rows=[
            {"id": 198, "_distance": None, "_match_score": 2.5, "_score": 2.5},
            {"id": 101, "_distance": None, "_match_score": 2.4, "_score": 2.4},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 2.3},
        ],
        expected=[
            {"id": 198, "_distance": None, "_match_score": 2.5, "_score": 0.01639},
            {"id": 101, "_distance": None, "_match_score": 2.4, "_score": 0.01613},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 0.01587},
        ],
    ),
]


@pytest.mark.parametrize("test_case", RRF_TEST_CASES, ids=lambda x: x.name)
def test_rrf_fusion(test_case: RRFFusionTestCase):
    vs_rows = create_rows_from_list(test_case.vs_rows)
    fts_rows = create_rows_from_list(test_case.fts_rows)

    keys, rows = fusion_result_rows_by_rrf(vs_rows, fts_rows, get_row_id, k=60)

    assert keys == ["id", "_distance", "_match_score", "_score"]
    assert len(rows) == len(test_case.expected)
    for row, exp in zip(rows, test_case.expected):
        assert row.id == exp["id"]
        if exp["_distance"] is not None:
            assert abs(row._distance - exp["_distance"]) < 1e-5
        else:
            assert row._distance is None
        if exp["_match_score"] is not None:
            assert abs(row._match_score - exp["_match_score"]) < 1e-5
        else:
            assert row._match_score is None
        assert abs(row._score - exp["_score"]) < 1e-5


# Test cases for Weighted fusion.

class WeightedFusionTestCase:
    def __init__(
        self,
        name: str,
        vs_rows: List[Dict],
        fts_rows: List[Dict],
        expected: List[Dict],
        vs_weight: float = 0.5,
        fts_weight: float = 0.5,
    ):
        self.name = name
        self.vs_rows = vs_rows
        self.fts_rows = fts_rows
        self.expected = expected
        self.vs_weight = vs_weight
        self.fts_weight = fts_weight


WEIGHTED_TEST_CASES = [
    WeightedFusionTestCase(
        name="vs_rows_and_fts_rows_equal_weights",
        vs_rows=[
            {"id": 101, "_distance": 0.1, "_match_score": None, "_score": 0.9},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.8},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.7},
            {"id": 198, "_distance": 0.4, "_match_score": None, "_score": 0.6},
            {"id": 175, "_distance": 0.5, "_match_score": None, "_score": 0.5},
        ],
        fts_rows=[
            {"id": 198, "_distance": None, "_match_score": 2.5, "_score": 2.5},
            {"id": 101, "_distance": None, "_match_score": 2.4, "_score": 2.4},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 2.3},
            {"id": 175, "_distance": None, "_match_score": 2.2, "_score": 2.2},
            {"id": 250, "_distance": None, "_match_score": 2.1, "_score": 2.1},
        ],
        expected=[
            {"id": 175, "_distance": 0.5, "_match_score": 2.2, "_score": 0.80391},
            {"id": 198, "_distance": 0.4, "_match_score": 2.5, "_score": 0.78540},
            {"id": 101, "_distance": 0.1, "_match_score": 2.4, "_score": 0.63784},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 0.58033},
            {"id": 250, "_distance": None, "_match_score": 2.1, "_score": 0.56319},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.14573},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.09870},
        ],
        vs_weight=0.5,
        fts_weight=0.5,
    ),
    WeightedFusionTestCase(
        name="vs_rows_and_fts_rows_vs_weighted",
        vs_rows=[
            {"id": 101, "_distance": 0.1, "_match_score": None, "_score": 0.9},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.8},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.7},
        ],
        fts_rows=[
            {"id": 101, "_distance": None, "_match_score": 2.4, "_score": 2.4},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 2.3},
            {"id": 250, "_distance": None, "_match_score": 2.1, "_score": 2.1},
        ],
        expected=[
            {"id": 101, "_distance": 0.1, "_match_score": 2.4, "_score": 0.31494},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.23317},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 0.23213},
            {"id": 250, "_distance": None, "_match_score": 2.1, "_score": 0.22528},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.15792},
        ],
        vs_weight=0.8,
        fts_weight=0.2,
    ),
    WeightedFusionTestCase(
        name="empty_fts_rows",
        vs_rows=[
            {"id": 101, "_distance": 0.1, "_match_score": None, "_score": 0.9},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.8},
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.7},
        ],
        fts_rows=[],
        expected=[
            {"id": 150, "_distance": 0.3, "_match_score": None, "_score": 0.14573},
            {"id": 203, "_distance": 0.2, "_match_score": None, "_score": 0.09870},
            {"id": 101, "_distance": 0.1, "_match_score": None, "_score": 0.04983},
        ],
        vs_weight=0.5,
        fts_weight=0.5,
    ),
    WeightedFusionTestCase(
        name="empty_vs_rows",
        vs_rows=[],
        fts_rows=[
            {"id": 198, "_distance": None, "_match_score": 2.5, "_score": 2.5},
            {"id": 101, "_distance": None, "_match_score": 2.4, "_score": 2.4},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 2.3},
        ],
        expected=[
            {"id": 198, "_distance": None, "_match_score": 2.5, "_score": 0.59514},
            {"id": 101, "_distance": None, "_match_score": 2.4, "_score": 0.58800},
            {"id": 110, "_distance": None, "_match_score": 2.3, "_score": 0.58033},
        ],
        vs_weight=0.5,
        fts_weight=0.5,
    ),
]


@pytest.mark.parametrize("test_case", WEIGHTED_TEST_CASES, ids=lambda x: x.name)
def test_weighted_fusion(test_case: WeightedFusionTestCase):
    vs_rows = create_rows_from_list(test_case.vs_rows)
    fts_rows = create_rows_from_list(test_case.fts_rows)

    keys, rows = fusion_result_rows_by_weighted(
        vs_rows, fts_rows, get_row_id, vs_weight=test_case.vs_weight, fts_weight=test_case.fts_weight
    )

    assert keys == ["id", "_distance", "_match_score", "_score"]
    assert len(rows) == len(test_case.expected)
    for row, exp in zip(rows, test_case.expected):
        assert row.id == exp["id"]
        if exp["_distance"] is not None:
            assert abs(row._distance - exp["_distance"]) < 1e-5
        else:
            assert row._distance is None
        if exp["_match_score"] is not None:
            assert abs(row._match_score - exp["_match_score"]) < 1e-5
        else:
            assert row._match_score is None
        assert abs(row._score - exp["_score"]) < 1e-5
