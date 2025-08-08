from typing import Any, Optional, List
from pathlib import Path

from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType
from pytidb.schema import Field
from FlagEmbedding import BGEM3FlagModel


class BGEM3EmbeddingFunction(BaseEmbeddingFunction):
    """
    A custom embedding function that uses BGE-M3 model for text embeddings.
    BGE-M3 is a versatile embedding model that supports dense retrieval, sparse retrieval, and multi-vector retrieval.
    """

    use_fp16: bool = Field(
        True, description="Whether to use FP16 precision for faster inference"
    )
    device: Optional[str] = Field(
        None, description="Device to run the model on (auto-detected if None)"
    )

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize BGE-M3 embedding function.

        Args:
            model_name: The BGE-M3 model name (default: "BAAI/bge-m3")
            use_fp16: Whether to use FP16 precision for faster inference
            device: Device to run the model on (auto-detected if None)
            **kwargs: Additional arguments
        """
        # BGE-M3 has fixed dimensions of 1024
        super().__init__(
            model_name=model_name,
            dimensions=1024,  # BGE-M3 fixed dimensions
            use_fp16=use_fp16,
            device=device,
            **kwargs,
        )

        self._model = BGEM3FlagModel(
            self.model_name, use_fp16=self.use_fp16, device=self.device
        )

    def _encode_text(self, text: str) -> List[float]:
        """
        Encode text using BGE-M3 model.

        Args:
            text: Input text to encode

        Returns:
            Dense embedding vector as list of floats
        """
        # Use BGE-M3 to encode text
        output = self._model.encode(text, return_dense=True)

        # Extract dense vector and convert to list
        dense_vector = output["dense_vecs"]

        # Handle both single text (1D array) and batch (2D array) cases
        if len(dense_vector.shape) == 1:
            return dense_vector.tolist()
        else:
            return dense_vector[0].tolist()

    def get_query_embedding(
        self, query: Any, source_type: Optional[EmbeddingSourceType] = "text", **kwargs
    ) -> List[float]:
        """
        Get embedding for a query.

        Args:
            query: Query text string input
            source_type: The type of source data ("text")
            **kwargs: Additional keyword arguments

        Returns:
            List of float values representing the embedding
        """
        if source_type == "text":
            text_input = str(query)
        else:
            raise ValueError(f"BGE-M3 can only process text input, unsupported source_type: {source_type}")

        return self._encode_text(text_input)

    def get_source_embedding(
        self, source: Any, source_type: Optional[EmbeddingSourceType] = "text", **kwargs
    ) -> List[float]:
        """
        Get embedding for a source field value.

        Args:
            source: Source field value
            source_type: The type of source data ("text")
            **kwargs: Additional keyword arguments

        Returns:
            List of float values representing the embedding
        """
        if source_type == "text":
            text_input = str(source)
        else:
            raise ValueError(f"BGE-M3 can only process text input, unsupported source_type: {source_type}")

        return self._encode_text(text_input)

    def get_source_embeddings(
        self,
        sources: List[Any],
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> List[List[float]]:
        """
        Get embeddings for multiple source field values.

        Args:
            sources: List of source field values
            source_type: The type of source data ("text")
            **kwargs: Additional keyword arguments

        Returns:
            List of embeddings, where each embedding is a list of float values
        """
        # Batch processing for efficiency
        if source_type == "text":
            text_inputs = [str(source) for source in sources]
        else:
                        raise ValueError(f"BGE-M3 can only process text input, unsupported source_type: {source_type}")

        # Batch encode all texts
        output = self._model.encode(text_inputs, return_dense=True)
        dense_vectors = output["dense_vecs"]

        # Convert to list of lists
        return [vector.tolist() for vector in dense_vectors]
