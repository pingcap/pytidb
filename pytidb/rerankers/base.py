from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel


class RerankResult(BaseModel):
    index: int
    relevance_score: float


class BaseReranker(ABC):
    @abstractmethod
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_n: Optional[int] = None,
    ) -> List[RerankResult]:
        raise NotImplementedError()
