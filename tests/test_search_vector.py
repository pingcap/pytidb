import os
from typing import Any

import pytest

from pytidb import TiDBClient, Table
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import DistanceMetric, TableModel, Field, Column
from pytidb.datatype import Vector
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

    tbl = client.create_table(schema=Chunk, mode="overwrite")

    # Prepare test data.
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


@pytest.fixture(scope="module")
def reranker():
    return Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_API_KEY"),
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


def test_prefilter_search(vector_table: Table):
    """Test vector search with prefilter enabled."""
    # Test prefilter with metadata filter
    results = (
        vector_table.search([1, 2, 3])
        .distance_metric(metric=DistanceMetric.COSINE)
        .filter({"user_id": 2}, prefilter=True)
        .limit(2)
        .to_list()
    )
    
    assert len(results) == 1
    assert results[0]["text"] == "bar"
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0
    assert results[0]["_score"] == 1


def test_prefilter_vs_postfilter(vector_table: Table):
    """Test that prefilter and postfilter return the same results for basic cases."""
    query_vector = [1, 2, 3]
    filters = {"user_id": {"$in": [2, 3]}}
    
    # Postfilter results (default)
    postfilter_results = (
        vector_table.search(query_vector)
        .filter(filters, prefilter=False)
        .limit(10)
        .to_list()
    )
    
    # Prefilter results
    prefilter_results = (
        vector_table.search(query_vector)
        .filter(filters, prefilter=True)
        .limit(10)
        .to_list()
    )
    
    # Should return same results for this simple case
    assert len(postfilter_results) == len(prefilter_results)
    assert len(postfilter_results) == 2
    
    # Sort by id for comparison
    postfilter_results.sort(key=lambda x: x["id"])
    prefilter_results.sort(key=lambda x: x["id"])
    
    for post, pre in zip(postfilter_results, prefilter_results):
        assert post["id"] == pre["id"]
        assert post["text"] == pre["text"]
        assert post["user_id"] == pre["user_id"]
        assert abs(post["_distance"] - pre["_distance"]) < 1e-6
        assert abs(post["_score"] - pre["_score"]) < 1e-6


def test_prefilter_with_distance_threshold(vector_table: Table):
    """Test prefilter with distance threshold."""
    results = (
        vector_table.search([1, 2, 3])
        .distance_threshold(0.01)
        .filter({"user_id": {"$in": [1, 2]}}, prefilter=True)
        .limit(10)
        .to_list()
    )
    
    # Should only return the exact match (user_id=2, distance=0)
    assert len(results) == 1
    assert results[0]["user_id"] == 2
    assert results[0]["_distance"] == 0


def test_prefilter_with_distance_range(vector_table: Table):
    """Test prefilter with distance range."""
    results = (
        vector_table.search([1, 2, 3])
        .distance_range(0.0, 0.001)  # Even smaller range
        .filter({"user_id": {"$in": [1, 2, 3]}}, prefilter=True)
        .debug(True)
        .limit(10)
        .to_list()
    )
    
    # Should only return results within distance range (exact match only)
    assert len(results) >= 1  # At least one result should match
    for result in results:
        assert 0.0 <= result["_distance"] <= 0.001  # All results should be within range


def test_prefilter_debug_mode(vector_table: Table):
    """Test that prefilter works with debug mode enabled."""
    results = (
        vector_table.search([1, 2, 3])
        .filter({"user_id": 2}, prefilter=True)
        .debug(True)
        .limit(2)
        .to_list()
    )
    
    assert len(results) == 1
    assert results[0]["text"] == "bar"
    assert results[0]["user_id"] == 2
