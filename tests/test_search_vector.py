import os
from typing import Any

import pytest

from pytidb import TiDBClient, Table
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import DistanceMetric, TableModel, Field, Column
from pytidb.datatype import Vector, JSON
from pytidb.search import SCORE_LABEL


# Vector Search


@pytest.fixture(scope="module")
def vector_table(client: TiDBClient):
    class Chunk(TableModel):
        __tablename__ = "test_vector_search"
        id: int = Field(None, primary_key=True)
        text: str = Field(None)
        text_vec: Any = Field(sa_column=Column(Vector(3)))
        user_id: int = Field(None)
        meta: dict = Field(sa_type=JSON)

    tbl = client.create_table(schema=Chunk, if_exists="overwrite")

    # Prepare test data.
    tbl.bulk_insert(
        [
            Chunk(
                id=1, text="foo", text_vec=[4, 5, 6], user_id=1, meta={"owner_id": 1}
            ),
            Chunk(
                id=2, text="bar", text_vec=[1, 2, 3], user_id=2, meta={"owner_id": 2}
            ),
            Chunk(
                id=3, text="biz", text_vec=[7, 8, 9], user_id=3, meta={"owner_id": 3}
            ),
        ]
    )

    return tbl


def test_vector_search(vector_table: Table):
    # to_pydantic()
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.L2)
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
    assert results[0][SCORE_LABEL] == 1
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


def test_with_distance_range(vector_table: Table):
    results = (
        vector_table.search([1, 2, 3]).distance_range(0.02, 0.05).limit(10).to_list()
    )

    assert len(results) == 2
    assert results[0]["id"] == 1
    assert results[0]["text"] == "foo"
    assert results[0]["user_id"] == 1
    assert abs(results[0]["_distance"] - 0.0254) < 1e-3

    assert results[1]["id"] == 3
    assert results[1]["text"] == "biz"
    assert results[1]["user_id"] == 3
    assert abs(results[1]["_distance"] - 0.0408) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_filter(vector_table: Table, prefilter: bool):
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.COSINE)
        .debug(True)
        .filter({"user_id": {"$in": [1, 2]}}, prefilter=prefilter)
        .limit(10)
        .to_list()
    )

    assert len(results) == 2
    assert results[0]["id"] == 2
    assert results[0]["text"] == "bar"
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1

    assert results[1]["id"] == 1
    assert results[1]["text"] == "foo"
    assert results[1]["user_id"] == 1
    assert abs(results[1]["_distance"] - 0.02547) < 1e-3
    assert abs(results[1]["_score"] - 0.97463) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_metadata_filter(vector_table: Table, prefilter: bool):
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.COSINE)
        .debug(True)
        .filter({"meta.owner_id": {"$in": [1, 2]}}, prefilter=prefilter)
        .limit(10)
        .to_list()
    )

    assert len(results) == 2
    assert results[0]["id"] == 2
    assert results[0]["text"] == "bar"
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1

    assert results[1]["id"] == 1
    assert results[1]["text"] == "foo"
    assert results[1]["user_id"] == 1
    assert abs(results[1]["_distance"] - 0.02547) < 1e-3
    assert abs(results[1]["_score"] - 0.97463) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_filter_and_distance_threshold(vector_table: Table, prefilter: bool):
    """Test prefilter with distance threshold."""
    results = (
        vector_table.search([1, 2, 3])
        .distance_threshold(0.03)  # Only Chunk #1 and #2 are within the threshold.
        .filter(
            {"user_id": 1}, prefilter=prefilter
        )  # Filter on user_id=1, only Chunk #1 is left.
        .limit(10)
        .to_list()
    )

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["text"] == "foo"
    assert results[0]["user_id"] == 1
    assert abs(results[0]["_distance"] - 0.0254) < 1e-3


@pytest.mark.parametrize("prefilter", [True, False], ids=["prefilter", "postfilter"])
def test_with_filter_and_distance_range(vector_table: Table, prefilter: bool):
    results = (
        vector_table.search([1, 2, 3])
        .distance_range(0.02, 0.05)  # Chunk #1 and #3 are within the range.
        .filter(
            {"user_id": 1}, prefilter=prefilter
        )  # Filter on user_id=1, only Chunk #1 is left.
        .limit(10)
        .to_list()
    )

    assert len(results) == 1
    assert results[0]["id"] == 1
    assert results[0]["text"] == "foo"
    assert results[0]["user_id"] == 1
    assert abs(results[0]["_distance"] - 0.0254) < 1e-3


@pytest.fixture(scope="module")
def reranker():
    return Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_AI_API_KEY"),
    )


def test_rerank(vector_table: Table, reranker: BaseReranker):
    reranked_results = (
        vector_table.search(search_type="vector")
        .vector([1, 2, 3])
        .text("bar")
        .rerank(reranker, "text")
        .limit(3)
        .to_list()
    )

    assert len(reranked_results) > 0
    assert reranked_results[0]["text"] == "bar"
    assert reranked_results[0]["_score"] > 0


def test_with_multi_vector_fields(client: TiDBClient):
    class ChunkWithMultiVec(TableModel):
        __tablename__ = "test_vector_search_multi_vec"
        id: int = Field(None, primary_key=True)
        title: str = Field(None)
        title_vec: list[float] = Field(sa_column=Column(Vector(3)))
        body: str = Field(None)
        body_vec: list[float] = Field(sa_column=Column(Vector(3)))

    tbl = client.create_table(schema=ChunkWithMultiVec, if_exists="overwrite")
    tbl.bulk_insert(
        [
            ChunkWithMultiVec(
                id=1, title="tree", title_vec=[4, 5, 6], body="cat", body_vec=[1, 2, 3]
            ),
            ChunkWithMultiVec(
                id=2, title="grass", title_vec=[1, 2, 3], body="dog", body_vec=[7, 8, 9]
            ),
            ChunkWithMultiVec(
                id=3, title="leaf", title_vec=[7, 8, 9], body="bird", body_vec=[4, 5, 6]
            ),
        ]
    )

    with pytest.raises(ValueError, match="more than two vector columns"):
        tbl.search([1, 2, 3], search_type="vector").limit(3).to_list()

    with pytest.raises(ValueError, match="Invalid vector column"):
        tbl.search([1, 2, 3], search_type="vector").vector_column("title").limit(3)

    with pytest.raises(ValueError, match="Non-exists vector column"):
        tbl.search([1, 2, 3], search_type="vector").vector_column(
            "non_exist_column"
        ).limit(3)

    with pytest.raises(ValueError, match="Invalid vector column name"):
        tbl.search([1, 2, 3], search_type="vector").vector_column(None).limit(3)

    results = (
        tbl.search([1, 2, 3], search_type="vector")
        .vector_column("title_vec")
        .limit(3)
        .to_list()
    )
    assert len(results) == 3
    assert results[0]["id"] == 2
    assert results[0]["title"] == "grass"
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1

    results = (
        tbl.search([1, 2, 3], search_type="vector")
        .vector_column("body_vec")
        .limit(3)
        .to_list()
    )
    assert len(results) == 3
    assert results[0]["id"] == 1
    assert results[0]["body"] == "cat"
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1
