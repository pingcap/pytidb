# Hybrid Search

Hybrid search is a technique that combines multiple search algorithms to deliver more accurate and relevant results. 

TiDB's support both semantic search (also termed vector search) and keyword-based search (also known as full-text search). You can leverage the strengths of both approaches to achieve better search results via hybrid search.

## Basic Usage



```python
from pytidb.rerankers import Reranker

jinaai = Reranker(model_name="jina_ai/jina-reranker-m0")

res = (
    table.search(
        "A library for my artificial intelligence software", search_type="hybrid"
    )
    .rerank(jinaai, "text")  # Rerank the result set with Jina AI reranker.
    .limit(3)
    .to_pandas()
)
res
``` 