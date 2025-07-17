from typing import Optional
from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field


def test_auto_embedding(shared_client: TiDBClient):
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

    tbl = shared_client.create_table(schema=Chunk, if_exists="overwrite")

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

    # Test dict insert
    dict_chunk = tbl.insert({"id": 5, "text": "dict_test", "user_id": 5})
    assert dict_chunk.id == 5
    assert dict_chunk.text == "dict_test"
    assert dict_chunk.user_id == 5
    assert len(dict_chunk.text_vec) == 1536

    # Test dict bulk_insert
    dict_chunks = tbl.bulk_insert(
        [
            {"id": 6, "text": "dict_bulk_1", "user_id": 6},
            {"id": 7, "text": "dict_bulk_2", "user_id": 7},
            {
                "id": 8,
                "text": "",
                "user_id": 8,
            },  # Empty string will skip auto embedding
        ]
    )
    assert len(dict_chunks) == 3
    assert dict_chunks[0].id == 6
    assert dict_chunks[0].text == "dict_bulk_1"
    assert len(dict_chunks[0].text_vec) == 1536
    assert dict_chunks[1].id == 7
    assert dict_chunks[1].text == "dict_bulk_2"
    assert len(dict_chunks[1].text_vec) == 1536
    assert dict_chunks[2].id == 8
    assert dict_chunks[2].text == ""
    assert dict_chunks[2].text_vec is None

    # Test mixed bulk_insert (dict and model instances)
    mixed_chunks = tbl.bulk_insert(
        [
            Chunk(id=9, text="model_instance", user_id=9),
            {"id": 10, "text": "dict_mixed", "user_id": 10},
        ]
    )
    assert len(mixed_chunks) == 2
    assert mixed_chunks[0].id == 9
    assert mixed_chunks[0].text == "model_instance"
    assert len(mixed_chunks[0].text_vec) == 1536
    assert mixed_chunks[1].id == 10
    assert mixed_chunks[1].text == "dict_mixed"
    assert len(mixed_chunks[1].text_vec) == 1536

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
