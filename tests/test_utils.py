from typing import Optional
from sqlalchemy import Row
from sqlalchemy.engine.result import result_tuple
from pytidb.utils import build_tidb_dsn, merge_result_rows


def test_build_tidb_dsn():
    # For TiDB Serverless
    dsn = build_tidb_dsn(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="xxxxxxxx.root",
        password="$password$",
    )
    assert dsn.host == "gateway01.us-west-2.prod.aws.tidbcloud.com"
    assert dsn.port == 4000
    assert dsn.username == "xxxxxxxx.root"
    assert dsn.password == "%24password%24"
    assert dsn.path == "/test"
    assert dsn.query == "ssl_verify_cert=true&ssl_verify_identity=true"
    assert (
        str(dsn)
        == "mysql+pymysql://xxxxxxxx.root:%24password%24@gateway01.us-west-2.prod.aws.tidbcloud.com:4000/test?ssl_verify_cert=true&ssl_verify_identity=true"
    )

    # For TiDB Cluster on local.
    dsn = build_tidb_dsn(host="localhost", username="root", password="password")
    assert dsn.host == "localhost"
    assert dsn.port == 4000
    assert dsn.username == "root"
    assert dsn.password == "password"
    assert dsn.path == "/test"
    assert dsn.query is None
    assert str(dsn) == "mysql+pymysql://root:password@localhost:4000/test"


def test_merge_result_rows():
    # Define test data structure
    fields_a = ["user_id", "name", "score"]
    fields_b = ["user_id", "city", "score"]
    row_factory_a = result_tuple(fields_a)
    row_factory_b = result_tuple(fields_b)

    # Prepare test data for set A
    rows_a = [
        row_factory_a([1, "Alice", 85]),  # score not None, should keep this
        row_factory_a([2, "Bob", None]),  # score None, should take from secondary
        row_factory_a([3, "Charlie", 95]),  # score not None, should keep this
    ]

    # Prepare test data for set B
    rows_b = [
        row_factory_b([2, "London", 88]),  # should override primary's None
        row_factory_b([3, "Paris", 92]),  # should not override primary's value
        row_factory_b([4, "Berlin", 78]),  # only in secondary
    ]

    def get_row_id(row: Row) -> Optional[int]:
        return row.user_id

    merged_fields, merged_rows = merge_result_rows(rows_a, rows_b, get_row_id)
    merged_by_id = {row.user_id: row for row in merged_rows}

    # Verify merged fields
    assert merged_fields == ["user_id", "name", "score", "city"]

    # Verify row present only in primary set
    alice = merged_by_id[1]
    assert alice.name == "Alice"
    assert alice.score == 85
    assert alice.city is None

    # Verify row with None score in primary set
    bob = merged_by_id[2]
    assert bob.name == "Bob"
    assert bob.city == "London"
    assert bob.score == 88  # Takes score from secondary

    # Verify row with non-None score in both sets
    charlie = merged_by_id[3]
    assert charlie.name == "Charlie"
    assert charlie.city == "Paris"
    assert charlie.score == 95  # Keeps score from primary

    # Verify row present only in secondary set
    david = merged_by_id[4]
    assert david.name is None
    assert david.city == "Berlin"
    assert david.score == 78

    # Verify edge cases
    empty_fields, empty_rows = merge_result_rows([], rows_b, get_row_id)
    assert empty_rows == rows_b
    assert empty_fields == ["user_id", "city", "score"]

    empty_fields, empty_rows = merge_result_rows(rows_a, [], get_row_id)
    assert empty_rows == rows_a
    assert empty_fields == ["user_id", "name", "score"]


def test_merge_result_rows_with_fusion():
    fields_a = ["id", "score", "distance"]
    fields_b = ["id", "score", "distance"]
    row_factory_a = result_tuple(fields_a)
    row_factory_b = result_tuple(fields_b)

    rows_a = [
        row_factory_a([1, 85, 2]),
        row_factory_a([2, None, 200]),  # score is None in rows_a
        row_factory_a([3, 95, 10]),
    ]

    rows_b = [
        row_factory_b([1, 90, 50]),
        row_factory_b([2, 88, 10]),
        row_factory_b([3, 92, None]),  # distance is None in rows_b
    ]

    def sum_fusion(
        value_a: Optional[float], value_b: Optional[float], row_a: Row, row_b: Row
    ) -> Optional[float]:
        return (value_a or 0) + (value_b or 0)

    def multiply_fusion(
        value_a: Optional[float], value_b: Optional[float], row_a: Row, row_b: Row
    ) -> Optional[float]:
        return (value_a or 1) * (value_b or 1)

    merge_strategies = {"score": sum_fusion, "distance": multiply_fusion}

    def get_row_id(row: Row) -> Optional[int]:
        return row.id

    _, merged_rows = merge_result_rows(rows_a, rows_b, get_row_id, merge_strategies)
    rows_by_id = {row.id: row for row in merged_rows}

    # Case 1: Both values present - sum score and multiply distance
    assert rows_by_id[1].score == 175  # 85 + 90
    assert rows_by_id[1].distance == 100  # 2 * 50

    # Case 2: Score None in rows_a
    assert rows_by_id[2].score == 88  # 0 (None) + 88 = 88
    assert rows_by_id[2].distance == 2000  # 200 * 10

    # Case 3: Distance None in rows_b
    assert rows_by_id[3].score == 187  # 95 + 92
    assert rows_by_id[3].distance == 10  # 10 * 1 (None)
