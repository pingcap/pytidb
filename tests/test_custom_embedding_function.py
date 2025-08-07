import hashlib
from typing import Any, Optional, List
from pathlib import Path

from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType


class CustomEmbeddingFunction(BaseEmbeddingFunction):
    """
    A custom embedding function that generates embeddings using a simple hash-based approach.
    This is useful for testing and demonstration purposes.
    """

    def __init__(
        self, model_name: str = "custom-hash-model", dimensions: int = 384, **kwargs
    ):
        super().__init__(model_name=model_name, dimensions=dimensions, **kwargs)

    def _text_to_embedding(self, text: str) -> List[float]:
        """
        Convert text to embedding using a deterministic hash-based approach.
        """
        # Normalize text
        text = str(text).strip().lower()

        # Create multiple hash values to generate vector components
        embedding = []
        for i in range(self.dimensions):
            # Use different seeds for each dimension
            hash_input = f"{text}_{i}"
            hash_obj = hashlib.md5(hash_input.encode())
            # Convert hash to float between -1 and 1
            hash_int = int(hash_obj.hexdigest()[:8], 16)
            normalized_value = (hash_int / (16**8)) * 2 - 1
            embedding.append(normalized_value)

        return embedding

    def _process_image_input(self, image_input: Any) -> str:
        """
        Process image input and convert to string representation for embedding.
        """
        if hasattr(image_input, "filename"):
            # PIL Image with filename
            return f"image_{image_input.filename}"
        elif isinstance(image_input, Path):
            return f"image_{image_input.name}"
        elif isinstance(image_input, str):
            # Could be URL or path
            return f"image_{image_input}"
        else:
            # Fallback to string representation
            return f"image_{str(image_input)}"

    def _get_embedding(
        self, query: Any, source_type: Optional[EmbeddingSourceType] = "text", **kwargs
    ) -> List[float]:
        if source_type == "text":
            text_input = str(query)
        elif source_type == "image":
            text_input = self._process_image_input(query)
        else:
            raise ValueError(f"Unsupported source_type: {source_type}")

        return self._text_to_embedding(text_input)

    def get_query_embedding(
        self, query: Any, source_type: Optional[EmbeddingSourceType] = "text", **kwargs
    ) -> List[float]:
        return self._get_embedding(query, source_type, **kwargs)

    def get_source_embedding(
        self, source: Any, source_type: Optional[EmbeddingSourceType] = "text", **kwargs
    ) -> List[float]:
        return self._get_embedding(source, source_type, **kwargs)

    def get_source_embeddings(
        self,
        sources: List[Any],
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> List[List[float]]:
        """
        Get embeddings for multiple source field values.
        """
        embeddings = []
        for source in sources:
            embedding = self.get_source_embedding(source, source_type, **kwargs)
            embeddings.append(embedding)

        return embeddings


# Test cases to verify the implementation
def test_custom_embedding_function():
    """Test the CustomEmbeddingFunction implementation."""

    # Initialize the custom embedding function
    embed_fn = CustomEmbeddingFunction(dimensions=128)

    # Test text embedding
    text_query = "hello world"
    text_embedding = embed_fn.get_query_embedding(text_query, "text")

    assert len(text_embedding) == 128
    assert all(isinstance(x, float) for x in text_embedding)

    # Test consistency - same input should produce same output
    text_embedding2 = embed_fn.get_query_embedding(text_query, "text")
    assert text_embedding == text_embedding2

    # Test source embedding
    source_text = "sample document"
    source_embedding = embed_fn.get_source_embedding(source_text, "text")
    assert len(source_embedding) == 128

    # Test batch embeddings
    sources = ["doc1", "doc2", "doc3"]
    batch_embeddings = embed_fn.get_source_embeddings(sources, "text")
    assert len(batch_embeddings) == 3
    assert all(len(emb) == 128 for emb in batch_embeddings)

    # Test image input
    image_path = "test_image.jpg"
    image_embedding = embed_fn.get_query_embedding(image_path, "image")
    assert len(image_embedding) == 128
