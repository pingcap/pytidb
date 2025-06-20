import os
import pytest

from pytidb import TiDBClient, Table
from pytidb.embeddings import EmbeddingFunction
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import TableModel, Field
from pytidb.datatype import Text


@pytest.fixture(scope="module")
def hybrid_table(client: TiDBClient):
    embed_fn = EmbeddingFunction("openai/text-embedding-3-small")

    class Item(TableModel, table=True):
        __tablename__ = "items_for_hybrid"
        id: int = Field(None, primary_key=True)
        name: str = Field()
        description: str = Field(sa_type=Text)
        embedding: list[float] = embed_fn.VectorField(source_field="description")

    tbl = client.create_table(schema=Item, mode="overwrite")

    # Prepare test data.
    tbl.bulk_insert(
        [
            Item(
                id=1,
                name="TiDB",
                description="TiDB is a distributed database supports HTAP and AI workloads.",
            ),
            Item(
                id=2,
                name="LlamaIndex",
                description="LlamaIndex is a framework for building AI applications.",
            ),
            Item(
                id=3,
                name="GPT-4",
                description="GPT-4 is a large language model developed by OpenAI.",
            ),
        ]
    )

    if not tbl.has_fts_index("description"):
        tbl.create_fts_index("description")

    return tbl


# Test case with various result formats.


def test_hybrid_search_to_list(hybrid_table: Table):
    expected_results = [
        {"id": 1, "_distance": 0.46569, "_match_score": 1.75128, "_score": 0.03279},
        {"id": 2, "_distance": 0.60269, "_match_score": 0.79679, "_score": 0.03226},
    ]
    actual_results = (
        hybrid_table.search("AI database", search_type="hybrid")
        .text_column("description")
        .limit(2)
        .to_list()
    )

    assert len(actual_results) == len(expected_results)
    for actual, expected in zip(actual_results, expected_results):
        assert actual["id"] == expected["id"]
        # FIXME: The diff between actual and expected should be less than 1e-5.
        assert abs(actual["_distance"] - expected["_distance"]) < 1e-3
        assert abs(actual["_match_score"] - expected["_match_score"]) < 1
        assert abs(actual["_score"] - expected["_score"]) < 1e-5


def test_hybrid_search_to_rows(hybrid_table: Table):
    expected_results = [
        {"id": 1, "_distance": 0.46569, "_match_score": 1.75128, "_score": 0.03279},
        {"id": 2, "_distance": 0.60269, "_match_score": 0.79679, "_score": 0.03226},
    ]
    actual_results = (
        hybrid_table.search("AI database", search_type="hybrid")
        .text_column("description")
        .limit(2)
        .to_rows()
    )

    assert len(actual_results) == len(expected_results)
    for actual, expected in zip(actual_results, expected_results):
        assert actual.id == expected["id"]
        # FIXME: The diff between actual and expected should be less than 1e-5.
        assert abs(actual._mapping["_distance"] - expected["_distance"]) < 1e-3
        assert abs(actual._mapping["_match_score"] - expected["_match_score"]) < 1
        assert abs(actual._mapping["_score"] - expected["_score"]) < 1e-5


def test_hybrid_search_to_pydantic(hybrid_table: Table):
    expected_results = [
        {"id": 1, "_distance": 0.46569, "_match_score": 1.75128, "_score": 0.03279},
        {"id": 2, "_distance": 0.60269, "_match_score": 0.79679, "_score": 0.03226},
    ]
    actual_results = (
        hybrid_table.search("AI database", search_type="hybrid")
        .text_column("description")
        .limit(2)
        .to_pydantic()
    )

    assert len(actual_results) == len(expected_results)
    for actual, expected in zip(actual_results, expected_results):
        assert actual.id == expected["id"]
        # FIXME: The diff between actual and expected should be less than 1e-5.
        assert abs(actual.distance - expected["_distance"]) < 1e-3
        assert abs(actual.match_score - expected["_match_score"]) < 1
        assert abs(actual.score - expected["_score"]) < 1e-5


def test_hybrid_search_to_pandas(hybrid_table: Table):
    expected_results = [
        {"id": 1, "_distance": 0.46569, "_match_score": 1.75128, "_score": 0.03279},
        {"id": 2, "_distance": 0.60269, "_match_score": 0.79679, "_score": 0.03226},
    ]
    actual_results = (
        hybrid_table.search("AI database", search_type="hybrid")
        .text_column("description")
        .limit(2)
        .to_pandas()
    )

    assert len(actual_results) == len(expected_results)
    for actual, expected in zip(actual_results.iloc, expected_results):
        assert actual.id == expected["id"]
        assert abs(actual._distance - expected["_distance"]) < 1e-3
        assert abs(actual._match_score - expected["_match_score"]) < 1
        assert abs(actual._score - expected["_score"]) < 1e-5


# Hybrid search with reranker.


@pytest.fixture(scope="module")
def reranker():
    return Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_API_KEY"),
    )


def test_rerank(hybrid_table: Table, reranker: BaseReranker):
    reranked_results = (
        hybrid_table.search(search_type="hybrid")
        .text("An AI library to develop AI applications")
        .text_column("description")
        .rerank(reranker, "description")
        .limit(2)
        .to_list()
    )
    expected_results = [
        {"id": 2, "name": "LlamaIndex"},
        {"id": 1, "name": "TiDB"},
    ]

    assert len(reranked_results) == len(expected_results)
    for actual, expected in zip(reranked_results, expected_results):
        assert actual["id"] == expected["id"]
        assert actual["name"] == expected["name"]
        assert actual["_distance"] > 0
        assert actual["_match_score"] > 0
        assert actual["_score"] > 0
