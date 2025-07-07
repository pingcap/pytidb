from pathlib import Path
from typing import List, Any, Literal, Optional, Union, TYPE_CHECKING

from pydantic import Field
from pytidb.embeddings.base import BaseEmbeddingFunction
from pytidb.embeddings.utils import encode_image_to_base64, parse_url_if_valid

if TYPE_CHECKING:
    from PIL.Image import Image


def get_embeddings(
    model_name: str,
    input: List[str],
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    timeout: Optional[int] = 60,
    **kwargs: Any,
) -> List[List[float]]:
    """
    Retrieve embeddings for a given list of input strings using the specified model.

    Args:
        api_key (str): The API key for authentication.
        api_base (str): The base URL of the LiteLLM proxy server.
        model_name (str): The name of the model to use for generating embeddings.
        input (List[str]): A list of input strings for which embeddings are to be generated.
        timeout (float): The timeout value for the API call, default 60 secs.
        **kwargs (Any): Additional keyword arguments to be passed to the embedding function.

    Returns:
        List[List[float]]: A list of embeddings, where each embedding corresponds to an input string.
    """
    from litellm import embedding

    response = embedding(
        api_key=api_key,
        api_base=api_base,
        model=model_name,
        input=input,
        timeout=timeout,
        **kwargs,
    )
    return [result["embedding"] for result in response.data]


EmbeddingSourceValueType = Union[str, Path, Image]

EmbeddingSourceType = Union[Literal["text"], Literal["image"]]


class BuiltInEmbeddingFunction(BaseEmbeddingFunction):
    api_key: Optional[str] = Field(None, description="The API key for authentication.")
    api_base: Optional[str] = Field(
        None, description="The base URL of the model provider."
    )
    timeout: Optional[int] = Field(
        None, description="The timeout value for the API call."
    )

    def __init__(
        self,
        model_name: str,
        dimensions: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            **kwargs,
        )
        if dimensions is None:
            self.dimensions = len(self.get_query_embedding("test"))

    def _process_source(
        self,
        source: EmbeddingSourceValueType,
        source_type: Optional[EmbeddingSourceType] = "text",
    ) -> Union[str, dict]:
        """
        Process source value based on source type and format.

        Args:
            source: Input source (string, Path or PIL Image object)
            source_type: Type of the source ("text" or "image")

        Returns:
            Processed input suitable for embedding generation

        Raises:
            ValueError: If the source format is not supported
        """
        if source_type == "image":
            return self._process_image_source(source)
        else:
            return source

    def _process_image_source(self, source: EmbeddingSourceValueType) -> dict:
        if isinstance(source, Path):
            source = "file://" + str(source.resolve())

        if isinstance(source, str):
            is_valid, image_url = parse_url_if_valid(source)
            if is_valid:
                if image_url.scheme == "file":
                    file_path = image_url.path
                    return {"image": encode_image_to_base64(file_path)}
                elif image_url.scheme == "http" or image_url.scheme == "https":
                    return {"image": image_url.geturl()}
                else:
                    raise ValueError(
                        f"invalid url schema for image source: {image_url.scheme}"
                    )
            else:
                raise ValueError(f"invalid url format for image source: {source}")
        elif isinstance(source, "PIL.Image.Image"):
            return {"image": encode_image_to_base64(source)}
        else:
            raise ValueError(
                "invalid input for source, current supported input types: "
                "url string, Path object, PIL.Image object"
            )

    def _process_image_query(self, query: EmbeddingSourceValueType) -> dict:
        if isinstance(query, Path):
            query = "file://" + str(query.resolve())

        if isinstance(query, str):
            is_valid, image_url = parse_url_if_valid(query)
            if is_valid:
                if image_url.scheme == "file":
                    file_path = image_url.path
                    return {"image": encode_image_to_base64(file_path)}
                elif image_url.scheme == "http" or image_url.scheme == "https":
                    return {"image": image_url.geturl()}
                else:
                    raise ValueError(
                        f"invalid url schema for image source: {image_url.scheme}"
                    )
            else:
                return query
        elif isinstance(query, Image):
            return {"image": encode_image_to_base64(query)}
        else:
            raise ValueError(
                "invalid input for image vector search, current supported input types: "
                "url string, Path object, PIL.Image object"
            )

    def get_query_embedding(
        self,
        query: EmbeddingSourceValueType,
        source_type: Optional[EmbeddingSourceType] = "text",
    ) -> list[float]:
        """
        Get embedding for a query. Currently only supports text queries.

        Args:
            query: Query text string or PIL Image object

        Returns:
            List of float values representing the embedding
        """
        if source_type == "text":
            embedding_input = query
        elif source_type == "image":
            embedding_input = self._process_image_query(query)
        else:
            raise ValueError(f"invalid source type: {source_type}")

        embeddings = get_embeddings(
            api_key=self.api_key,
            api_base=self.api_base,
            model_name=self.model_name,
            dimensions=self.dimensions,
            timeout=self.timeout,
            input=[embedding_input],
        )
        return embeddings[0]

    def get_source_embedding(
        self,
        source: EmbeddingSourceValueType,
        source_type: Optional[EmbeddingSourceType] = "text",
    ) -> list[float]:
        embedding_input = self._process_source(source, source_type)
        embeddings = get_embeddings(
            api_key=self.api_key,
            api_base=self.api_base,
            model_name=self.model_name,
            dimensions=self.dimensions,
            timeout=self.timeout,
            input=[embedding_input],
        )
        return embeddings[0]

    def get_source_embeddings(
        self,
        sources: List[EmbeddingSourceValueType],
        source_type: Optional[EmbeddingSourceType] = "text",
    ) -> list[list[float]]:
        embedding_inputs = [
            self._process_source(source, source_type) for source in sources
        ]
        embeddings = get_embeddings(
            api_key=self.api_key,
            api_base=self.api_base,
            model_name=self.model_name,
            dimensions=self.dimensions,
            timeout=self.timeout,
            input=embedding_inputs,
        )
        return embeddings
