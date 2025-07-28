from typing import Optional
from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field


def test_auto_embedding(shared_client: TiDBClient, text_embed: EmbeddingFunction):
    class ChunkForAutoEmbedding(TableModel):
        __tablename__ = "test_auto_embedding"
        id: int = Field(primary_key=True)
        text: str = Field()
        text_vec: Optional[list[float]] = text_embed.VectorField(
            source_field="text",
            index=False,
        )
        user_id: int = Field()

    Chunk = ChunkForAutoEmbedding
    tbl = shared_client.create_table(schema=Chunk, if_exists="overwrite")

    # Test insert with auto embedding
    chunk = tbl.insert(Chunk(id=1, text="foo", user_id=1))
    assert len(chunk.text_vec) == 1536

    # Test dict insert with auto embedding
    chunk = tbl.insert({"id": 2, "text": "bar", "user_id": 1})
    assert len(chunk.text_vec) == 1536

    # Test bulk_insert with auto embedding (including empty text case)
    chunks_via_model_instance = [
        Chunk(id=3, text="baz", user_id=2),
        Chunk(id=4, text="", user_id=2),  # Empty string will skip auto embedding.
    ]
    chunks_via_dict = [
        {
            "id": 5,
            "text": "qux",
            "user_id": 3,
        },  # Empty string will skip auto embedding.
        {"id": 6, "text": "", "user_id": 3},
    ]
    chunks = tbl.bulk_insert(chunks_via_model_instance + chunks_via_dict)
    for chunk in chunks:
        if chunk.text == "":
            assert chunk.text_vec is None
        else:
            assert len(chunk.text_vec) == 1536

    # Test vector search with auto embedding
    results = tbl.search("bar").limit(1).to_pydantic(with_score=True)
    assert len(results) == 1
    assert results[0].id == 2
    assert results[0].text == "bar"
    assert results[0].similarity_score >= 0.9

    # Test update with auto embedding, from empty to non-empty string
    chunk = tbl.get(4)
    assert chunk.text == ""
    assert chunk.text_vec is None
    tbl.update(values={"text": "another baz"}, filters={"id": 4})
    updated_chunk = tbl.get(4)
    assert updated_chunk.text == "another baz"
    assert len(updated_chunk.text_vec) == 1536

    # Test update with auto embedding, from non-empty to empty string
    tbl.update(values={"text": ""}, filters={"id": 4})
    updated_chunk = tbl.get(4)
    assert updated_chunk.text == ""
    assert updated_chunk.text_vec is None

    # Test save with auto embedding
    saved_chunk = tbl.save(Chunk(id=7, text="save_test", user_id=4))
    assert saved_chunk.text == "save_test"
    assert len(saved_chunk.text_vec) == 1536

    # Test save with empty string - should skip auto embedding
    save_empty = tbl.save(Chunk(id=8, text="", user_id=4))
    assert save_empty.text == ""
    assert save_empty.text_vec is None

    # Test save with pre-existing vector field - should skip auto embedding
    existing_vector = [0.1] * 1536
    save_with_vector = tbl.save(
        Chunk(id=9, text="save_with_vector", text_vec=existing_vector, user_id=4)
    )
    assert len(save_with_vector.text_vec) == 1536

    # Test save update from empty to text - should trigger auto embedding
    saved_chunk = tbl.get(6)
    saved_chunk.text = "another qux"
    tbl.save(saved_chunk)
    assert len(saved_chunk.text_vec) == 1536
