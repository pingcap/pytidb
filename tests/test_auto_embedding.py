from typing import Optional
import pytest
from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field


@pytest.fixture(scope="function")
def text_embed(request):
    """Parametrized EmbeddingFunction fixture for both client-side and server-side embedding"""
    use_server = request.param
    if use_server:
        # For server-side embedding, use TiDB Cloud free model
        return EmbeddingFunction(
            "openai/text-embedding-3-small",
            timeout=20,
            use_server=True,
        )
    else:
        # For client-side embedding, use OpenAI model
        return EmbeddingFunction(
            "openai/text-embedding-3-small", timeout=20, use_server=False
        )


@pytest.mark.parametrize(
    "text_embed", [False, True], indirect=True, ids=["client_side", "server_side"]
)
def test_auto_embedding(shared_client: TiDBClient, text_embed: EmbeddingFunction):
    embed_mode = "server_side" if text_embed.use_server else "client_side"

    class ChunkForAutoEmbedding(TableModel):
        __tablename__ = f"test_auto_embedding_{embed_mode}"
        id: int = Field(primary_key=True)
        text: Optional[str] = Field()
        text_vec: Optional[list[float]] = text_embed.VectorField(
            source_field="text",
            index=False,
        )
        user_id: int = Field()

    Chunk = ChunkForAutoEmbedding
    tbl = shared_client.create_table(schema=Chunk, if_exists="overwrite")

    # Test insert with auto embedding
    chunk = tbl.insert(Chunk(id=1, text="foo", user_id=1))
    assert len(chunk.text_vec) == text_embed.dimensions

    # Test dict insert with auto embedding
    chunk = tbl.insert({"id": 2, "text": "bar", "user_id": 1})
    assert len(chunk.text_vec) == text_embed.dimensions

    # Test bulk_insert with auto embedding (including empty text case)
    chunks_via_model_instance = [
        Chunk(id=3, text="baz", user_id=2),
        Chunk(id=4, text=None, user_id=2),  # None will skip auto embedding.
    ]
    chunks_via_dict = [
        {"id": 5, "text": "qux", "user_id": 3},
        {"id": 6, "text": None, "user_id": 3},  # None will skip auto embedding.
    ]
    chunks = tbl.bulk_insert(chunks_via_model_instance + chunks_via_dict)
    for chunk in chunks:
        if chunk.text is None:
            assert chunk.text_vec is None
        else:
            assert len(chunk.text_vec) == text_embed.dimensions

    # Test vector search with auto embedding
    results = tbl.search("bar").limit(1).to_pydantic(with_score=True)
    assert len(results) == 1
    assert results[0].id == 2
    assert results[0].text == "bar"
    assert results[0].similarity_score >= 0.9

    # Test update with auto embedding, from empty to non-empty string
    chunk = tbl.get(4)
    assert chunk.text is None
    assert chunk.text_vec is None

    tbl.update(values={"text": "another baz"}, filters={"id": 4})
    updated_chunk = tbl.get(4)
    assert updated_chunk.text == "another baz"
    assert len(updated_chunk.text_vec) == text_embed.dimensions

    # Test update with auto embedding, from non-empty to empty string
    tbl.update(values={"text": None}, filters={"id": 4})
    updated_chunk = tbl.get(4)
    assert updated_chunk.text is None
    assert updated_chunk.text_vec is None

    # Test save with auto embedding
    saved_chunk = tbl.save(Chunk(id=7, text="save_test", user_id=4))
    assert saved_chunk.text == "save_test"
    assert len(saved_chunk.text_vec) == text_embed.dimensions

    # Test save with None - should skip auto embedding
    save_empty = tbl.save(Chunk(id=8, text=None, user_id=4))
    assert save_empty.text is None
    assert save_empty.text_vec is None

    # Test saving with a pre-existing vector field.
    existing_vector = [0.1] * text_embed.dimensions
    if not text_embed.use_server:
        # If server-side auto embedding is enabled, manual updates to the vector field should be disallowed.
        save_with_vector = tbl.save(
            Chunk(id=9, text="save_with_vector", text_vec=existing_vector, user_id=4)
        )
        assert len(save_with_vector.text_vec) == text_embed.dimensions
    else:
        # If client-side auto embedding is enabled, saving with a provided vector should skip auto embedding.
        with pytest.raises(Exception):
            save_with_vector = tbl.save(
                Chunk(
                    id=9, text="save_with_vector", text_vec=existing_vector, user_id=4
                )
            )

    # Test save update from empty to text - should trigger auto embedding
    if not text_embed.use_server:
        # FIXME: The server-side auto embedding does not support empty string.
        saved_chunk = tbl.get(6)
        saved_chunk.text = "another qux"
        tbl.save(saved_chunk)
        assert len(saved_chunk.text_vec) == text_embed.dimensions
