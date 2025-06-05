import hashlib
from typing import Optional, Any
from sqlmodel import Field

from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel


def test_auto_embedding(client: TiDBClient):
    text_embed_small = EmbeddingFunction("openai/text-embedding-3-small")
    test_table_name = "test_auto_embedding"

    client.drop_table(test_table_name)

    class Chunk(TableModel, table=True):
        __tablename__ = test_table_name
        id: int = Field(primary_key=True)
        text: str = Field()
        # FIXME: if using list[float], sqlmodel will report an error
        text_vec: Optional[Any] = text_embed_small.VectorField(source_field="text")
        user_id: int = Field()

    tbl = client.create_table(schema=Chunk, mode="overwrite")

    tbl.truncate()
    tbl.insert(Chunk(id=1, text="foo", user_id=1))
    tbl.bulk_insert(
        [
            Chunk(id=2, text="bar", user_id=2),
            Chunk(id=3, text="baz", user_id=3),
            Chunk(id=4, text="qux", user_id=4),
        ]
    )
    chunks = tbl.query(
        filters={
            "user_id": 3,
        }
    )
    assert len(chunks) == 1
    assert chunks[0].text == "baz"
    assert len(chunks[0].text_vec) == 1536

    results = tbl.search("bar").limit(1).to_pydantic(with_score=True)
    assert len(results) == 1
    assert results[0].id == 2
    assert results[0].text == "bar"
    assert results[0].similarity_score >= 0.9

    # Update,
    chunk = tbl.get(1)
    assert chunk.text_vec is not None
    original_vec_hash = hashlib.md5(chunk.text_vec).hexdigest()
    tbl.update(
        values={"text": "new foo"},
        filters={"id": 1},
    )
    chunk = tbl.get(1)
    assert chunk.text_vec is not None
    updated_vec_hash = hashlib.md5(chunk.text_vec).hexdigest()
    assert original_vec_hash != updated_vec_hash
