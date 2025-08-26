import os
import pytest

from pytidb import TiDBClient, Table
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import TableModel, Field, FullTextField


@pytest.fixture(scope="module")
def text_table(shared_client: TiDBClient):
    # Skip fulltext search tests if not connected to TiDB Serverless
    if not shared_client.is_serverless:
        pytest.skip("Currently, Only TiDB Serverless supports full text indexes")

    class ChunkWithFullTextField(TableModel):
        __tablename__ = "test_fulltext_search"
        id: int = Field(primary_key=True)
        name: str = Field()
        description: str = FullTextField()

    Chunk = ChunkWithFullTextField
    tbl = shared_client.create_table(schema=Chunk, if_exists="overwrite")

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

    shared_client.execute(f"ALTER TABLE {tbl._sa_table.name} COMPACT;")

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
        api_key=os.getenv("JINA_AI_API_KEY"),
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


def test_with_multiple_text_fields(shared_client: TiDBClient):
    # Skip test if not connected to TiDB Serverless
    if not shared_client.is_serverless:
        pytest.skip("Currently, Only TiDB Serverless supports full text indexes")

    class Article(TableModel):
        __tablename__ = "test_fts_with_multi_text_fields"
        id: int = Field(primary_key=True)
        title: str = FullTextField()
        body: str = FullTextField()

    tbl = shared_client.create_table(schema=Article, if_exists="overwrite")
    tbl.bulk_insert(
        [
            Article(
                id=1,
                title="TiDB",
                body="TiDB is a distributed SQL database compatible with MySQL.",
            ),
            Article(
                id=2,
                title="LlamaIndex",
                body="LlamaIndex is a framework for building AI applications.",
            ),
            Article(
                id=3,
                title="OpenAI",
                body="OpenAI provides APIs for building AI models and applications.",
            ),
        ]
    )

    with pytest.raises(ValueError):
        tbl.search("TiDB", search_type="fulltext").limit(2).to_list()

    results = (
        tbl.search("TiDB", search_type="fulltext")
        .text_column("title")
        .limit(2)
        .to_list()
    )
    assert len(results) == 1
    assert results[0]["title"] == "TiDB"
    assert "TiDB" in results[0]["body"]
    assert results[0]["_match_score"] > 0
    assert results[0]["_score"] == results[0]["_match_score"]

    results = (
        tbl.search("AI framework", search_type="fulltext")
        .text_column("body")
        .limit(2)
        .to_list()
    )
    assert len(results) == 2
    assert results[0]["title"] == "LlamaIndex"
    assert "LlamaIndex" in results[0]["body"]
    assert results[0]["_match_score"] > 0
    assert results[0]["_score"] == results[0]["_match_score"]
