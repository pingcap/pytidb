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
    "cohere/embed-v4.0": 1536,
    "cohere/embed-english-v3.0": 1024,
    "cohere/embed-multilingual-v3.0": 1024,
    # Jina AI models
    "jina_ai/jina-embeddings-v4": 2048,
    "jina_ai/jina-embeddings-v3": 1024,
    "jina_ai/jina-clip-v2": 1024,
    # Gemini models
    "gemini/gemini-embedding-001": 3072,
    # Hugging Face models
    "huggingface/Alibaba-NLP/gme-Qwen2-VL-2B-Instruct": 1536,
    "huggingface/Alibaba-NLP/gme-Qwen2-VL-7B-Instruct": 3584,
    "huggingface/Alibaba-NLP/gte-Qwen1.5-7B-instruct": 4096,
    "huggingface/Alibaba-NLP/gte-Qwen2-1.5B-instruct": 8960,
    "huggingface/Alibaba-NLP/gte-Qwen2-7B-instruct": 3584,
    "huggingface/Alibaba-NLP/gte-multilingual-base": 768,
    "huggingface/Alibaba-NLP/gte-modernbert-base": 768,
    "huggingface/Alibaba-NLP/gte-base-en-v1.5": 768,
    "huggingface/BAAI/bge-base-en": 768,
    "huggingface/BAAI/bge-base-en-v1.5": 768,
    "huggingface/BAAI/bge-base-zh": 768,
    "huggingface/BAAI/bge-base-zh-v1.5": 768,
    "huggingface/BAAI/bge-en-icl": 4096,
    "huggingface/BAAI/bge-large-en": 1024,
    "huggingface/BAAI/bge-large-en-v1.5": 1024,
    "huggingface/BAAI/bge-large-zh": 1024,
    "huggingface/BAAI/bge-large-zh-v1.5": 1024,
    "huggingface/BAAI/bge-m3": 1024,
    "huggingface/BAAI/bge-m3-unsupervised": 1024,
    "huggingface/BAAI/bge-multilingual-gemma2": 3584,
    "huggingface/BAAI/bge-small-en": 512,
    "huggingface/BAAI/bge-small-en-v1.5": 512,
    "huggingface/BAAI/bge-small-zh": 512,
    "huggingface/BAAI/bge-small-zh-v1.5": 512,
    "huggingface/Cohere/Cohere-embed-multilingual-v3.0": 1024,
    "huggingface/Qwen/Qwen3-Embedding-0.6B": 1024,
    "huggingface/Qwen/Qwen3-Embedding-4B": 2560,
    "huggingface/Qwen/Qwen3-Embedding-8B": 4096,
    "huggingface/Snowflake/snowflake-arctic-embed-l": 1024,
    "huggingface/Snowflake/snowflake-arctic-embed-l-v2.0": 1024,
    "huggingface/Snowflake/snowflake-arctic-embed-m": 768,
    "huggingface/Snowflake/snowflake-arctic-embed-m-long": 768,
    "huggingface/Snowflake/snowflake-arctic-embed-m-v1.5": 768,
    "huggingface/Snowflake/snowflake-arctic-embed-m-v2.0": 768,
    "huggingface/Snowflake/snowflake-arctic-embed-s": 384,
    "huggingface/Snowflake/snowflake-arctic-embed-xs": 384,
    "huggingface/intfloat/e5-base": 768,
    "huggingface/intfloat/e5-base-v2": 768,
    "huggingface/intfloat/e5-large": 1024,
    "huggingface/intfloat/e5-large-v2": 1024,
    "huggingface/intfloat/e5-mistral-7b-instruct": 4096,
    "huggingface/intfloat/e5-small": 384,
    "huggingface/intfloat/e5-small-v2": 384,
    "huggingface/intfloat/multilingual-e5-base": 768,
    "huggingface/intfloat/multilingual-e5-large": 1024,
    "huggingface/intfloat/multilingual-e5-large-instruct": 1024,
    "huggingface/intfloat/multilingual-e5-small": 384,
    "huggingface/jinaai/jina-embedding-b-en-v1": 768,
    "huggingface/jinaai/jina-embedding-s-en-v1": 512,
    "huggingface/jinaai/jina-embeddings-v2-base-en": 768,
    "huggingface/jinaai/jina-embeddings-v2-small-en": 512,
    "huggingface/jinaai/jina-embeddings-v3": 1024,
    "huggingface/jinaai/jina-embeddings-v4": 2048,
    # Nvidia NIM models
    "nvidia_nim/baai/bge-m3": 1024,
    "nvidia_nim/nvidia/nv-embed-v1": 4096,
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
