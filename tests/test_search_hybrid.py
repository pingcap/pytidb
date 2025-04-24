import os
import pytest

from pytidb import TiDBClient, Table
from pytidb.embeddings import EmbeddingFunction
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import TableModel, Field


@pytest.fixture(scope="module")
def hybrid_table(db: TiDBClient):
    text_embed_small = EmbeddingFunction("openai/text-embedding-3-small")

    class Chunk(TableModel, table=True):
        __tablename__ = "chunks_for_hybrid"
        id: int = Field(None, primary_key=True)
        text: str = Field(None)
        text_vec: list[float] = text_embed_small.VectorField(source_field="text")
        user_id: int = Field(None)

    tbl = db.create_table(schema=Chunk)

    # Prepare test data.
    tbl.delete()
    tbl.bulk_insert(
        [
            Chunk(
                id=1,
                text="TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads.",
                user_id=1,
            ),
            Chunk(
                id=2,
                text="LlamaIndex is a framework for building AI applications.",
                user_id=2,
            ),
            Chunk(
                id=3,
                text="OpenAI is a company that provides a platform for building AI models.",
                user_id=3,
            ),
        ]
    )

    if not tbl.has_fts_index("text"):
        tbl.create_fts_index("text")

    return tbl


def test_hybrid_search(hybrid_table: Table):
    # to_pydantic()
    results = (
        hybrid_table.search("HTAP database", search_type="hybrid")
        .debug()
        .text_column("text")
        .limit(2)
        .to_pydantic()
    )
    assert len(results) == 2
    assert "TiDB" in results[0].text
    assert results[0].user_id == 1
    assert results[0].score > 0

    # to_pandas()
    results = (
        hybrid_table.search(search_type="hybrid")
        .text("Framework helps develop intelligent applications")
        .limit(2)
        .to_pandas()
    )
    assert results.size > 0
    assert "LlamaIndex" in results.iloc[0]["text"]
    assert results.iloc[0]["user_id"] == 2

    # to_list()
    results = (
        hybrid_table.search(search_type="hybrid").text("OpenAI").limit(2).to_list()
    )
    assert len(results) > 0
    assert "OpenAI" in results[0]["text"]
    assert results[0]["user_id"] == 3


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
        .rerank(reranker, "text")
        .limit(3)
        .to_list()
    )

    assert len(reranked_results) > 0
    assert "LlamaIndex" in reranked_results[0]["text"]
    assert reranked_results[0]["_score"] > 0
