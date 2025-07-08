from typing import Optional
from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field


def test_auto_embedding(client: TiDBClient):
    text_embed_small = EmbeddingFunction("openai/text-embedding-3-small")
    test_table_name = "test_auto_embedding"

    class Chunk(TableModel):
        __tablename__ = test_table_name
        id: int = Field(primary_key=True)
        text: str = Field()
        text_vec: Optional[list[float]] = text_embed_small.VectorField(
            source_field="text"
        )
        user_id: int = Field()

    tbl = client.create_table(schema=Chunk, mode="overwrite")

    tbl.insert(Chunk(id=1, text="foo", user_id=1))
    tbl.bulk_insert(
        [
            Chunk(id=2, text="bar", user_id=2),
            Chunk(id=3, text="baz", user_id=3),
            Chunk(
                id=4,
                text="",  # Empty string will skip auto embedding.
                user_id=4,
            ),
        ]
    )
    chunks = tbl.query(filters=Chunk.user_id == 3).to_pydantic()
    assert len(chunks) == 1
    assert chunks[0].text == "baz"
    assert len(chunks[0].text_vec) == 1536

    results = tbl.search("bar").limit(1).to_pydantic(with_score=True)
    assert len(results) == 1
    assert results[0].id == 2
    assert results[0].text == "bar"
    assert results[0].similarity_score >= 0.9

    # Update,
    chunk = tbl.get(4)
    assert chunk.text == ""
    assert chunk.text_vec is None
    tbl.update(
        values={"text": "qux"},
        filters={"id": 4},
    )
    chunk = tbl.get(4)
    assert chunk.text == "qux"
    assert chunk.text_vec is not None
