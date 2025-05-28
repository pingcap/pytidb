from typing import List, Dict
import pytest
from sqlalchemy import Row

from pytidb.fusion import fusion_result_rows_by_rrf
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
