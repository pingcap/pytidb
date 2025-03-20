from typing import Any

from pytidb import TiDBClient
from pytidb.schema import DistanceMetric, TableModel
from pytidb.search import SIMILARITY_SCORE_LABEL


# Vector Search


def test_vector_search(db: TiDBClient):
    from sqlalchemy import Column
    from tidb_vector.sqlalchemy import VectorType
    from sqlmodel import Field

    class Chunk(TableModel, table=True):
        __tablename__ = "test_vector_search"
        id: int = Field(None, primary_key=True)
        text: str = Field(None)
        text_vec: Any = Field(sa_column=Column(VectorType(3)))
        user_id: int = Field(None)

    tbl = db.create_table(schema=Chunk)
    tbl.truncate()
    tbl.bulk_insert(
        [
            Chunk(id=1, text="foo", text_vec=[4, 5, 6], user_id=1),
            Chunk(id=2, text="bar", text_vec=[1, 2, 3], user_id=2),
            Chunk(id=3, text="biz", text_vec=[7, 8, 9], user_id=3),
        ]
    )

    # to_pydantic()
    results = (
        tbl.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.COSINE)
        .num_candidate(20)
        .filter({"user_id": 2})
        .limit(2)
        .to_pydantic()
    )
    assert len(results) == 1
    assert results[0].text == "bar"
    assert results[0].similarity_score == 1
    assert results[0].score == 1
    assert results[0].user_id == 2

    # to_pandas()
    results = tbl.search([1, 2, 3]).limit(2).to_pandas()
    assert results.size > 0

    # to_list()
    results = tbl.search([1, 2, 3]).limit(2).to_list()
    assert len(results) > 0
    assert results[0]["text"] == "bar"
    assert results[0][SIMILARITY_SCORE_LABEL] == 1
    assert results[0]["score"] == 1
    assert results[0]["user_id"] == 2
