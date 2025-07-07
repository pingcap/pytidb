from .base import BaseEmbeddingFunction
from .bulitin import BuiltInEmbeddingFunction

EmbeddingFunction = BuiltInEmbeddingFunction

__all__ = ["BaseEmbeddingFunction", "EmbeddingFunction"]
