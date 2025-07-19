from pathlib import Path
from typing import TYPE_CHECKING, List, Any, Optional, Union

from pytidb.schema import Field
from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType
from pytidb.embeddings.utils import (
    encode_local_file_to_base64,
    encode_pil_image_to_base64,
    parse_url_safely,
)
import urllib.request


if TYPE_CHECKING:
    from PIL.Image import Image


SourceInputType = Union[str, Path, "Image"]
QueryInputType = Union[str, Path, "Image"]


def get_embeddings(
    model_name: str,
    input: List[str],
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    timeout: Optional[int] = 60,
    caching: bool = True,
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
        caching (bool): Whether to cache the embeddings, default True.
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
        caching=caching,
        **kwargs,
    )
    return [result["embedding"] for result in response.data]


# Map of model name -> maximum allowed base64 length (characters)
_MAX_B64_LENGTH_PER_MODEL = {
    # Despite the document says the input image size is up to 25MB,
    # according to the https://docs.aws.amazon.com/bedrock/latest/userguide/titan-multiemb-models.html,
    # the actual limit is 100k for base64 encoded string.
    "bedrock/amazon.titan-embed-image-v1": 100000,
}


class BuiltInEmbeddingFunction(BaseEmbeddingFunction):
    api_key: Optional[str] = Field(None, description="The API key for authentication.")
    api_base: Optional[str] = Field(
        None, description="The base URL of the model provider."
    )
    timeout: Optional[int] = Field(
        None, description="The timeout value for the API call."
    )
    caching: bool = Field(
        True, description="Whether to cache the embeddings, default True."
    )

    def __init__(
        self,
        model_name: str,
        dimensions: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[int] = None,
        caching: bool = True,
        **kwargs,
    ):
        super().__init__(
            model_name=model_name,
            dimensions=dimensions,
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            caching=caching,
            **kwargs,
        )
        if dimensions is None:
            self.dimensions = len(self.get_query_embedding("test", "text"))

    def _process_query(
        self, query: QueryInputType, source_type: Optional[EmbeddingSourceType] = "text"
    ) -> Union[str, dict]:
        if source_type == "text":
            return query
        elif source_type == "image":
            return self._process_image_query(query)
        else:
            raise ValueError(f"invalid source type: {source_type}")

    def _process_image_query(self, query: QueryInputType) -> Union[str, dict]:
        try:
            from PIL.Image import Image
        except ImportError:
            raise ImportError(
                "PIL (Pillow) is required for image processing. Install it with: pip install Pillow"
            )

        if isinstance(query, Path):
            query = query.resolve().as_uri()

        if isinstance(query, str):
            is_valid, image_url = parse_url_safely(query)
            if is_valid:
                if image_url.scheme == "file":
                    file_path = urllib.request.url2pathname(image_url.path)
                    max_len = _MAX_B64_LENGTH_PER_MODEL.get(self.model_name)
                    base64_str = encode_local_file_to_base64(
                        file_path, max_base64_length=max_len
                    )
                    # For bedrock models, prepend data URL prefix and return string
                    if self.model_name.startswith("bedrock/"):
                        return f"data:image/jpeg;base64,{base64_str}"
                    return {"image": base64_str}
                elif image_url.scheme == "http" or image_url.scheme == "https":
                    # For bedrock models, Bedrock API expects base64 not URL; fall back to query string.
                    if self.model_name.startswith("bedrock/"):
                        return image_url.geturl()
                    return {"image": image_url.geturl()}
                else:
                    raise ValueError(
                        f"invalid url schema for image source: {image_url.scheme}"
                    )
            else:
                # For image search, the query can be string contains some keywords.
                return query
        elif isinstance(query, Image):
            max_len = _MAX_B64_LENGTH_PER_MODEL.get(self.model_name)
            base64_str = encode_pil_image_to_base64(query, max_base64_length=max_len)
            if self.model_name.startswith("bedrock/"):
                return f"data:image/jpeg;base64,{base64_str}"
            return {"image": base64_str}
        else:
            raise ValueError(
                "invalid input for image vector search, current supported input types: "
                "url string, Path object, PIL.Image object"
            )

    def get_query_embedding(
        self,
        query: QueryInputType,
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> list[float]:
        """
        Get embedding for a query. Currently only supports text queries.

        Args:
            query: Query text string or PIL Image object
            source_type: The type of source data ("text" or "image")
            **kwargs: Additional keyword arguments to be passed to the embedding function.

        Returns:
            List of float values representing the embedding
        """
        embedding_input = self._process_query(query, source_type)
        embeddings = get_embeddings(
            api_key=self.api_key,
            api_base=self.api_base,
            model_name=self.model_name,
            dimensions=self.dimensions,
            timeout=self.timeout,
            caching=self.caching,
            input=[embedding_input],
            **kwargs,
        )
        return embeddings[0]

    def _process_source(
        self,
        source: SourceInputType,
        source_type: Optional[EmbeddingSourceType] = "text",
    ) -> Union[str, dict]:
        if source_type == "image":
            return self._process_image_source(source)
        elif source_type == "text":
            return source
        else:
            raise ValueError(f"Invalid source type: {source_type}")

    def _process_image_source(self, source: SourceInputType) -> Union[str, dict]:
        try:
            from PIL.Image import Image
        except ImportError:
            raise ImportError(
                "PIL (Pillow) is required for image processing. Install it with: pip install Pillow"
            )

        if isinstance(source, Path):
            source = source.resolve().as_uri()

        if isinstance(source, str):
            is_valid, image_url = parse_url_safely(source)
            if is_valid:
                if image_url.scheme == "file":
                    file_path = urllib.request.url2pathname(image_url.path)
                    max_len = _MAX_B64_LENGTH_PER_MODEL.get(self.model_name)
                    base64_str = encode_local_file_to_base64(
                        file_path, max_base64_length=max_len
                    )
                    if self.model_name.startswith("bedrock/"):
                        return f"data:image/jpeg;base64,{base64_str}"
                    return {"image": base64_str}
                elif image_url.scheme == "http" or image_url.scheme == "https":
                    # For bedrock models, Bedrock API expects base64 not URL; fall back to query string.
                    if self.model_name.startswith("bedrock/"):
                        return image_url.geturl()
                    return {"image": image_url.geturl()}
                else:
                    raise ValueError(
                        f"invalid url schema for image source: {image_url.scheme}"
                    )
            else:
                raise ValueError(f"invalid url format for image source: {source}")
        elif isinstance(source, Image):
            max_len = _MAX_B64_LENGTH_PER_MODEL.get(self.model_name)
            base64_str = encode_pil_image_to_base64(source, max_base64_length=max_len)
            if self.model_name.startswith("bedrock/"):
                return f"data:image/jpeg;base64,{base64_str}"
            return {"image": base64_str}
        else:
            raise ValueError(
                "invalid input for source, current supported input types: "
                "url string, Path object, PIL.Image object"
            )

    def get_source_embedding(
        self,
        source: SourceInputType,
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> list[float]:
        embedding_input = self._process_source(source, source_type)
        embeddings = get_embeddings(
            api_key=self.api_key,
            api_base=self.api_base,
            model_name=self.model_name,
            dimensions=self.dimensions,
            timeout=self.timeout,
            caching=self.caching,
            input=[embedding_input],
            **kwargs,
        )
        return embeddings[0]

    def get_source_embeddings(
        self,
        sources: List[SourceInputType],
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
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
            caching=self.caching,
            input=embedding_inputs,
            **kwargs,
        )
        return embeddings
