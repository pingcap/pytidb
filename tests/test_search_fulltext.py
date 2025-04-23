import os
import pytest

from pytidb import TiDBClient, Table
from pytidb.rerankers import Reranker
from pytidb.rerankers.base import BaseReranker
from pytidb.schema import TableModel, Field


@pytest.fixture(scope="module")
def text_table(db: TiDBClient):
    class Chunk(TableModel, table=True):
        __tablename__ = "test_fulltext_search"
        id: int = Field(None, primary_key=True)
        text: str = Field(None)
        user_id: int = Field(None)

    tbl = db.create_table(schema=Chunk)

    # Prepare test data.
    tbl.truncate()
    tbl.bulk_insert(
        [
            Chunk(id=1, text="foo", user_id=1),
            Chunk(id=2, text="bar", user_id=2),
            Chunk(id=3, text="biz", user_id=3),
        ]
    )

    if not tbl.has_fts_index("text"):
        tbl.create_fts_index("text", name="fts_idx_text_on_documents_for_fts")

    return tbl


def test_fulltext_search(text_table: Table):
    # to_pydantic()
    results = (
        text_table.search("foo", search_type="fulltext")
        .debug()
        .text_column("text")
        .limit(2)
        .to_pydantic()
    )
    assert len(results) == 1
    assert results[0].text == "foo"
    assert results[0].user_id == 1

    # to_pandas()
    results = text_table.search("bar", search_type="fulltext").limit(2).to_pandas()
    assert results.size > 0
    assert results.iloc[0]["text"] == "bar"
    assert results.iloc[0]["user_id"] == 2

    # to_list()
    results = text_table.search("biz", search_type="fulltext").limit(2).to_list()
    assert len(results) > 0
    assert results[0]["text"] == "biz"
    assert results[0]["user_id"] == 3


@pytest.fixture(scope="module")
def reranker():
    return Reranker(
        model_name="jina_ai/jina-reranker-v2-base-multilingual",
        api_key=os.getenv("JINA_API_KEY"),
    )


def test_rerank(text_table: Table, reranker: BaseReranker):
    reranked_results = (
        text_table.search("foo", search_type="fulltext")
        .rerank(reranker, "text")
        .limit(3)
        .to_list()
    )

    assert len(reranked_results) > 0
    assert reranked_results[0]["text"] == "foo"
    assert reranked_results[0]["_score"] > 0
