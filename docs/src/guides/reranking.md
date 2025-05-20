# Reranking

Reranking is a technique used to improve search results by reordering them based on weighted algorithms or specialized models.

## Model-based Rerankers

Model-based reranking uses specialized models to refine vector search results. 

The process works in two stages:

1. **Initial Retrieval**: Vector search identifies the top k most similar documents from the collection
2. **Reranking**: A reranking model evaluates these k documents and reorders them to produce the final top n results (where n ≤ k)

This two-stage retrieval approach significantly improves both document relevance and accuracy.

=== "Python"

    PyTiDB provides the `Reranker` class that allows you to use reranker models from multiple third-party providers.

    1. Create a reranker instance

        ```python
        from pytidb.rerankers import Reranker

        reranker = Reranker(model_name="{provider}/{model_name}")
        ```

    2. Apply reranker via `.rerank()` method

        ```python
        table.search("{query}").rerank(reranker, "{field_to_rerank}").limit(3)
        ```

### Supported Providers

Here are some examples to use reranker models from third-party providers.

#### Jina AI

To enable reranker provided by JinaAI, go to their [website](https://jina.ai/reranker) to create a API key.

For example:

```python
jinaai = Reranker(
    # Using the `jina-reranker-m0` model
    model_name="jina_ai/jina-reranker-m0",
    api_key="{your-jinaai-api-key}"
)
```