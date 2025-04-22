import os
from typing import Any

import pytest

from pytidb import TiDBClient, Table
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import DistanceMetric, TableModel, Field, Column
from pytidb.datatype import Vector
from pytidb.search import SIMILARITY_SCORE_LABEL


# Vector Search


@pytest.fixture(scope="module")
def vector_table(db: TiDBClient):
    class Chunk(TableModel, table=True):
        __tablename__ = "test_vector_search"
        id: int = Field(None, primary_key=True)
        text: str = Field(None)
        text_vec: Any = Field(sa_column=Column(Vector(3)))
        user_id: int = Field(None)

    tbl = db.create_table(schema=Chunk)

    # Prepare test data.
    tbl.truncate()
    tbl.bulk_insert(
        [
            Chunk(id=1, text="foo", text_vec=[4, 5, 6], user_id=1),
            Chunk(id=2, text="bar", text_vec=[1, 2, 3], user_id=2),
            Chunk(id=3, text="biz", text_vec=[7, 8, 9], user_id=3),
        ]
    )

    return tbl


def test_vector_search(vector_table: Table):
    # to_pydantic()
    results = (
        vector_table.search([1, 2, 3])
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
    results = vector_table.search([1, 2, 3]).limit(2).to_pandas()
    assert results.size > 0

    # to_list()
    results = vector_table.search([1, 2, 3]).limit(2).to_list()
    assert len(results) > 0
    assert results[0]["text"] == "bar"
    assert results[0][SIMILARITY_SCORE_LABEL] == 1
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1


def test_with_distance_threshold(vector_table: Table):
    result = (
        vector_table.search([1, 2, 3])
        .debug()
        .distance_threshold(0.01)
        .limit(10)
        .to_list()
    )
    assert len(result) == 1


@pytest.fixture(scope="module")
def reranker():
    return Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_API_KEY"),
    )


def test_rerank(vector_table: Table, reranker: BaseReranker):
    reranked_results = (
        vector_table.search({"query_embedding": [1, 2, 3], "query_str": "bar"})
        .rerank(reranker, "text")
        .to_list()
    )

    assert len(reranked_results) > 0
    assert reranked_results[0]["text"] == "bar"
    assert reranked_results[0]["_score"] > 0
