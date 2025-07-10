from .base import BaseEmbeddingFunction
from .builtin import BuiltInEmbeddingFunction

EmbeddingFunction = BuiltInEmbeddingFunction

__all__ = ["BaseEmbeddingFunction", "EmbeddingFunction"]
