import os
import pytest

from pytidb import TiDBClient, Table
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import TableModel, Field, FullTextField


@pytest.fixture(scope="module")
def text_table(client: TiDBClient):
    class Chunk(TableModel):
        __tablename__ = "test_fulltext_search"
        id: int = Field(primary_key=True)
        name: str = Field()
        description: str = FullTextField()

    tbl = client.create_table(schema=Chunk, mode="overwrite")

    # Prepare test data.
    tbl.bulk_insert(
        [
            Chunk(
                id=1,
                name="TiDB",
                description="TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads.",
            ),
            Chunk(
                id=2,
                name="LlamaIndex",
                description="LlamaIndex is a framework for building AI applications.",
            ),
            Chunk(
                id=3,
                name="OpenAI",
                description="OpenAI is a company that provides a platform for building AI models.",
            ),
        ]
    )

    return tbl


def test_fulltext_search(text_table: Table):
    # to_pydantic()
    results = (
        text_table.search("HTAP database", search_type="fulltext")
        .text_column("description")
        .debug()
        .limit(2)
        .to_pydantic()
    )
    assert len(results) == 1
    assert results[0].name == "TiDB"
    assert "TiDB" in results[0].description
    assert results[0].match_score > 0
    assert results[0].score == results[0].match_score

    # to_pandas()
    results = (
        text_table.search(search_type="fulltext")
        .text("AI framework")
        .limit(2)
        .to_pandas()
    )
    assert results.size > 0
    assert results.iloc[0]["name"] == "LlamaIndex"
    assert "LlamaIndex" in results.iloc[0]["description"]
    assert results.iloc[0]["_match_score"] > 0
    assert results.iloc[0]["_score"] == results.iloc[0]["_match_score"]

    # to_list()
    results = text_table.search("OpenAI", search_type="fulltext").limit(2).to_list()
    assert len(results) > 0
    assert results[0]["name"] == "OpenAI"
    assert "OpenAI" in results[0]["description"]
    assert results[0]["_match_score"] > 0
    assert results[0]["_score"] == results[0]["_match_score"]


@pytest.fixture(scope="module")
def reranker():
    return Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_API_KEY"),
    )


def test_rerank(text_table: Table, reranker: BaseReranker):
    reranked_results = (
        text_table.search(
            "An AI library to develop AI applications", search_type="fulltext"
        )
        .rerank(reranker, "description")
        .limit(3)
        .to_list()
    )

    assert len(reranked_results) > 0
    assert reranked_results[0]["name"] == "LlamaIndex"
    assert "LlamaIndex" in reranked_results[0]["description"]
    assert reranked_results[0]["_score"] > 0
