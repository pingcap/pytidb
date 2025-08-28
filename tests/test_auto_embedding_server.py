from typing import Optional
import os
import pytest
from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field


EMBEDDING_MODELS = [
    {
        "id": "openai",
        "model_name": "openai/text-embedding-3-small",
        "expected_similarity": 0.9,
    },
    {
        "id": "jina_ai",
        "model_name": "jina_ai/jina-embeddings-v3",
        "expected_similarity": 0.7,
    },
    {
        "id": "tidbcloud_free_titan",
        "model_name": "tidbcloud_free/amazon/titan-embed-text-v2",
        "expected_similarity": 0.9,
    },
    {
        "id": "tidbcloud_free_cohere",
        "model_name": "tidbcloud_free/cohere/embed-multilingual-v3",
        "expected_similarity": 0.7,
    },
    {
        "id": "cohere",
        "model_name": "cohere/embed-v4.0",
        "expected_similarity": 0.7,
    },
    {
        "id": "gemini",
        "model_name": "gemini/gemini-embedding-001",
        "expected_similarity": 0.8,
    },
    {
        "id": "huggingface",
        "model_name": "huggingface/intfloat/multilingual-e5-large",
        "expected_similarity": 0.9,
    },
    {
        "id": "nvidia_nim",
        "model_name": "nvidia_nim/baai/bge-m3",
        "expected_similarity": 0.9,
    },
]


def _should_skip(shared_client: TiDBClient, model_id: str) -> Optional[str]:
    # Skip auto embedding tests if not connected to TiDB Serverless
    if not shared_client.is_serverless:
        return "Currently, Only TiDB Serverless supports auto embedding"

    # Configure embedding provider based on model
    if model_id == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            return "OPENAI_API_KEY is not set"
        shared_client.configure_embedding_provider(
            "openai", os.getenv("OPENAI_API_KEY")
        )
    elif model_id == "jina_ai":
        if not os.getenv("JINA_AI_API_KEY"):
            return "JINA_AI_API_KEY is not set"
        shared_client.configure_embedding_provider(
            "jina_ai", os.getenv("JINA_AI_API_KEY")
        )
    elif model_id == "cohere":
        if not os.getenv("COHERE_API_KEY"):
            return "COHERE_API_KEY is not set"
        shared_client.configure_embedding_provider(
            "cohere", os.getenv("COHERE_API_KEY")
        )
    elif model_id == "gemini":
        if not os.getenv("GEMINI_API_KEY"):
            return "GEMINI_API_KEY is not set"
        shared_client.configure_embedding_provider(
            "gemini", os.getenv("GEMINI_API_KEY")
        )
    elif model_id == "huggingface":
        if not os.getenv("HUGGINGFACE_API_KEY"):
            return "HUGGINGFACE_API_KEY is not set"
        shared_client.configure_embedding_provider(
            "huggingface", os.getenv("HUGGINGFACE_API_KEY")
        )
    elif model_id == "nvidia_nim":
        if not os.getenv("NVIDIA_NIM_API_KEY"):
            return "NVIDIA_NIM_API_KEY is not set"
        shared_client.configure_embedding_provider(
            "nvidia_nim", os.getenv("NVIDIA_NIM_API_KEY")
        )
    elif model_id == "tidbcloud_free":
        # tidbcloud_free doesn't need additional API key configuration
        pass

    return None


@pytest.fixture(
    scope="module",
    params=EMBEDDING_MODELS,
    ids=[model["id"] for model in EMBEDDING_MODELS],
)
def text_embed(request):
    """Create EmbeddingFunction instances for each model in EMBEDDING_MODELS."""
    model_config = request.param
    embed_fn = EmbeddingFunction(
        model_name=model_config.get("model_name"),
        dimensions=model_config.get("dimensions"),
        timeout=30,
    )
    # Add model config for table naming
    embed_fn._model_config = model_config
    return embed_fn


def test_auto_embedding(shared_client: TiDBClient, text_embed: EmbeddingFunction):
    model_id = text_embed._model_config["id"]

    # Check if test should be skipped
    skip_reason = _should_skip(shared_client, model_id)
    if skip_reason:
        pytest.skip(skip_reason)

    class ChunkBase(TableModel, table=False):
        __tablename__ = f"chunks_with_{model_id}_auto_embedding"
        id: int = Field(primary_key=True)
        text: Optional[str] = Field()
        text_vec: Optional[list[float]] = text_embed.VectorField(
            source_field="text",
            index=False,
        )
        user_id: int = Field()

    Chunk = type(
        f"ChunkWith{model_id.capitalize()}AutoEmbedding", (ChunkBase,), {}, table=True
    )
    tbl = shared_client.create_table(schema=Chunk, if_exists="overwrite")

    # Test insert with auto embedding
    chunk = tbl.insert(Chunk(id=1, text="foo", user_id=1))
    assert len(chunk.text_vec) == text_embed.dimensions

    # Test dict insert with auto embedding
    chunk = tbl.insert({"id": 2, "text": "bar", "user_id": 1})
    assert len(chunk.text_vec) == text_embed.dimensions

    # Test bulk_insert with auto embedding (including empty text case)
    chunk_entities = [
        Chunk(id=3, text="baz", user_id=2),
        Chunk(id=4, text=None, user_id=2),  # None will skip auto embedding.
    ]
    chunk_dicts = [
        {"id": 5, "text": "qux", "user_id": 3},
        {"id": 6, "text": None, "user_id": 3},  # None will skip auto embedding.
    ]
    chunks = tbl.bulk_insert(chunk_entities + chunk_dicts)
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
    assert (
        results[0].similarity_score >= text_embed._model_config["expected_similarity"]
    )

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
    # When auto embedding is enabled, manual updates to the vector field should be disallowed.
    existing_vector = [0.1] * text_embed.dimensions
    with pytest.raises(Exception):
        tbl.save(
            Chunk(id=9, text="save_with_vector", text_vec=existing_vector, user_id=4)
        )

    # Test save update from empty to text - should trigger auto embedding
    # FIXME: The server-side auto embedding does not support empty string.
    saved_chunk = tbl.get(6)
    saved_chunk.text = "another qux"
    saved_chunk = tbl.save(saved_chunk)
    assert len(saved_chunk.text_vec) == text_embed.dimensions
