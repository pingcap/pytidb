from pytidb.rerankers.base import BaseReranker, RerankResult
from typing import List, Optional


class LiteLLMReranker(BaseReranker):
    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.model_name = model_name
        self.api_key = api_key
        self.api_base = api_base
        self.timeout = timeout

    def rerank(
        self, query: str, documents: List[str], top_n: Optional[int] = None
    ) -> List[RerankResult]:
        try:
            from litellm import rerank
        except Exception:
            raise ImportError(
                "Failed to import litellm, please install it with `pip install pytidb[models]` or `pip install litellm`"
            )

        res = rerank(
            model=self.model_name,
            query=query,
            documents=documents,
            top_n=top_n,
            api_key=self.api_key,
            api_base=self.api_base,
            timeout=self.timeout,
        )

        return [
            RerankResult(index=item["index"], relevance_score=item["relevance_score"])
            for item in res.results
        ]
