from pathlib import Path
from typing import TYPE_CHECKING, Any, List, Optional, Union

from pydantic import Field
from pytidb.embeddings.aliases import normalize_model_name
from pytidb.embeddings.base import BaseEmbeddingFunction, EmbeddingSourceType
from pytidb.embeddings.dimensions import KNOWN_MODEL_DIMENSIONS
from pytidb.embeddings.utils import (
    encode_local_file_to_base64,
    encode_pil_image_to_base64,
    parse_url_safely,
)
import urllib.request


if TYPE_CHECKING:
    from PIL.Image import Image


# Map of model name -> maximum allowed base64 length (characters)
_MAX_B64_LENGTH_PER_MODEL = {
    # Despite the document says the input image size is up to 25MB,
    # according to the https://docs.aws.amazon.com/bedrock/latest/userguide/titan-multiemb-models.html,
    # the actual limit is 100k for base64 encoded string.
    "bedrock/amazon.titan-embed-image-v1": 100000,
}


EmbeddingInput = Union[str, Path, "Image"]


def _validate_model_dimensions(
    model_name: str,
    dimensions: Optional[int],
) -> int:
    if dimensions is None:
        if model_name in KNOWN_MODEL_DIMENSIONS:
            dimensions = KNOWN_MODEL_DIMENSIONS.get(model_name)
        else:
            raise ValueError(
                f"Unknown dimensions for model {model_name}, please specify `dimensions` parameter."
            )
    return dimensions


def _get_provider_default_options(
    provider: str,
    model_name: str,
    dimensions: int,
) -> dict[str, Any]:
    if provider == "tidbcloud_free":
        if model_name == "tidbcloud_free/amazon/titan-embed-text-v2":
            return {"dimensions": dimensions}
        elif model_name.startswith("tidbcloud_free/cohere/"):
            default_dimensions = KNOWN_MODEL_DIMENSIONS.get(model_name)
            if dimensions != default_dimensions:
                raise ValueError(
                    f"Model {model_name} (output dimension: {default_dimensions}) does "
                    f"not support custom dimensions to {dimensions}."
                )
            return {
                "input_type": "search_document",
                "input_type@search": "search_query",
            }
        else:
            return {}
    elif provider == "openai":
        # Ref: https://platform.openai.com/docs/api-reference/embeddings/create
        return {"dimensions": dimensions}
    elif provider == "jina_ai":
        # Ref: https://jina.ai/embeddings/
        return {"dimensions": dimensions}
    elif provider == "cohere":
        # Ref: https://docs.cohere.com/reference/embed
        return {"output_dimension": dimensions}
    elif provider == "gemini":
        # Ref: https://ai.google.dev/api/embeddings
        return {"output_dimensionality": dimensions}
    elif provider in ("nvidia_nim", "hug"):
        # Provider huggingface does not support dimensions parameter.
        # Ref: https://huggingface.co/docs/inference-providers/tasks/feature-extraction
        return {}
    elif provider == "huggingface":
        # Provider huggingface does not support dimensions parameter.
        # Ref: https://huggingface.co/docs/inference-providers/tasks/feature-extraction
        return {}
    else:
        # Default behavior: do not pass dimensions parameter.
        return {}


class EmbeddingFunction(BaseEmbeddingFunction):
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
    multimodal: bool = Field(
        False,
        description=(
            "Indicates whether the embedding function supports multi-modal input (e.g., both text and image). "
            "Currently, multi-modal embedding is only supported for client-side embedding. "
            "- For multimodal=True, enable client-side embedding by default."
            "- For multimodal=False, disable server-side embedding by default."
        ),
    )

    def __init__(
        self,
        model_name: str,
        dimensions: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[int] = None,
        caching: bool = True,
        use_server: Optional[bool] = None,
        additional_json_options: Optional[dict[str, Any]] = None,
        multimodal: bool = False,
        **kwargs,
    ):
        if use_server is None:
            # If multimodal is False, use server-side embedding by default.
            # If multimodal is True, use client-side embedding by default.
            use_server = not multimodal

        model_name = normalize_model_name(model_name)
        if "/" not in model_name:
            raise ValueError(
                f"Invalid model name: {model_name}, model name should be "
                "in the format of <provider>/<model>."
            )
        provider = model_name.split("/")[0]
        _additional_json_options = {}

        if use_server:
            dimensions = _validate_model_dimensions(model_name, dimensions)
            provider_default_options = _get_provider_default_options(
                provider, model_name, dimensions
            )
            _additional_json_options.update(provider_default_options)
            _additional_json_options.update(additional_json_options or {})

        super().__init__(
            model_name=model_name,
            provider=provider,
            dimensions=dimensions,
            api_key=api_key,
            api_base=api_base,
            timeout=timeout,
            caching=caching,
            use_server=use_server,
            additional_json_options=_additional_json_options,
            multimodal=multimodal,
            **kwargs,
        )

        # For client-side embedding, try to infer dimensions with a test query.
        if not self.use_server and self.dimensions is None:
            embedding = self.get_query_embedding("test", "text")
            if embedding is None:
                raise ValueError(
                    f"Cannot infer dimensions for model {self.model_name}. Please specify `dimensions` parameter."
                )
            self.dimensions = len(embedding)

    def _process_input(
        self, input: EmbeddingInput, source_type: Optional[EmbeddingSourceType] = "text"
    ) -> Union[str, dict]:
        if source_type == "text":
            return input
        elif source_type == "image":
            return self._process_image_input(input)
        else:
            raise ValueError(f"Invalid source type: {source_type}")

    def _process_image_input(self, input: EmbeddingInput) -> Union[str, dict]:
        try:
            from PIL.Image import Image
        except ImportError:
            raise ImportError(
                "PIL (Pillow) is required for image processing. Install it with: pip install Pillow"
            )

        if isinstance(input, Path):
            input = input.resolve().as_uri()

        if isinstance(input, str):
            is_valid, image_url = parse_url_safely(input)
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
                return input
        elif isinstance(input, Image):
            max_len = _MAX_B64_LENGTH_PER_MODEL.get(self.model_name)
            base64_str = encode_pil_image_to_base64(input, max_base64_length=max_len)
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
        query: EmbeddingInput,
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> list[float]:
        """
        Get embedding for a query (text or image).

        Args:
            query: Query text string or PIL Image object
            source_type: The type of source data ("text" or "image")

        Returns:
            List of float values representing the embedding
        """
        embedding_input = self._process_input(query, source_type)
        embeddings = self._call_embeddings_api([embedding_input], **kwargs)
        return embeddings[0]

    def get_source_embedding(
        self,
        source: EmbeddingInput,
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> list[float]:
        """
        Get embedding for a source field value (typically text).

        Args:
            source: Source field value (text)
            source_type: The type of source data ("text" or "image")

        Returns:
            List of float values representing the embedding
        """
        embedding_input = self._process_input(source, source_type)
        embeddings = self._call_embeddings_api([embedding_input], **kwargs)
        return embeddings[0]

    def get_source_embeddings(
        self,
        sources: List[EmbeddingInput],
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> list[list[float]]:
        """
        Get embeddings for multiple source field values.

        Args:
            sources: List of source field values
            source_type: The type of source data ("text" or "image")

        Returns:
            List of embeddings, where each embedding is a list of float values
        """
        embedding_inputs = [
            self._process_input(source, source_type) for source in sources
        ]
        embeddings = self._call_embeddings_api(embedding_inputs, **kwargs)
        return embeddings

    def __call__(
        self,
        input: EmbeddingInput,
        source_type: Optional[EmbeddingSourceType] = "text",
        **kwargs,
    ) -> list[float]:
        return self._call_embeddings_api([input], **kwargs)

    def _call_embeddings_api(
        self, input: List[EmbeddingInput], **kwargs
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
        try:
            from litellm import embedding
        except ImportError:
            raise ImportError(
                "To use the built-in embedding function, you need to install pytidb[models] with: "
                "pip install pytidb[models]"
            )

        response = embedding(
            input=input,
            api_key=self.api_key,
            api_base=self.api_base,
            model=self.model_name,
            timeout=self.timeout,
            caching=self.caching,
            **kwargs,
        )
        return [result["embedding"] for result in response.data]
