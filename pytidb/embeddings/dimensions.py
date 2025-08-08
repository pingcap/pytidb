"""
Embedding model dimensions and aliases.

This module contains predefined dimensions for various embedding models
and mapping aliases for backward compatibility.
"""

from typing import Optional, List


# Dictionary mapping model names to their embedding dimensions
KNOWN_MODEL_DIMENSIONS = {
    # TiDB Cloud Free models
    "tidbcloud_free/amazon/titan-embed-text-v2": 1024,
    "tidbcloud_free/cohere/embed-english-v3": 1024,
    "tidbcloud_free/cohere/embed-multilingual-v3": 1024,
    # OpenAI models
    "openai/text-embedding-3-small": 1536,
    "openai/text-embedding-3-large": 3072,
    "openai/text-embedding-ada-002": 1536,
    # Cohere models
    "cohere/embed-english-v3.0": 1024,
    "cohere/embed-multilingual-v3.0": 1024,
    # Jina AI models
    "jina_ai/jina-embeddings-v4": 2048,
    "jina_ai/jina-embeddings-v3": 1024,
    "jina_ai/jina-clip-v2": 1024,
    # TODO: remove these after jina_ai is released on prod.
    "jina/jina-embeddings-v4": 2048,
    "jina/jina-embeddings-v3": 1024,
    "jina/jina-clip-v2": 1024,
}

# Mapping of model aliases to their full names for backward compatibility
MODEL_ALIASES = {
    "text-embedding-3-small": "openai/text-embedding-3-small",
    "text-embedding-3-large": "openai/text-embedding-3-large",
    "text-embedding-ada-002": "openai/text-embedding-ada-002",
}


def get_model_dimensions(model_name: str) -> Optional[int]:
    normalized_name = MODEL_ALIASES.get(model_name, model_name)
    return KNOWN_MODEL_DIMENSIONS.get(normalized_name)


def is_known_model(model_name: str) -> bool:
    normalized_name = MODEL_ALIASES.get(model_name, model_name)
    return normalized_name in KNOWN_MODEL_DIMENSIONS


def list_known_models() -> List[str]:
    return list(KNOWN_MODEL_DIMENSIONS.keys()) + list(MODEL_ALIASES.keys())


def register_model_dimension(model_name: str, dimensions: int):
    KNOWN_MODEL_DIMENSIONS[model_name] = dimensions


def register_model_alias(alias: str, canonical_name: str):
    MODEL_ALIASES[alias] = canonical_name
