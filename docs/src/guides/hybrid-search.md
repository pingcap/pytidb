# Hybrid Search

Hybrid search is a technique that combines multiple search algorithms to deliver more accurate and relevant results. 

TiDB supports both semantic search (also termed vector search) and keyword-based search (also known as full-text search). You can leverage the strengths of both approaches to achieve better search results via hybrid search.

!!! tip

    To check complete example of hybrid search, please refer to the [hybrid-search example](https://github.com/pingcap/pytidb/tree/main/examples/hybrid_search).

## Basic Usage

### Step 1. Create a table with a vector field and a full-text index

=== "Python"

    Assuming you have already [connected to your TiDB database](./connect.md) using `TiDBClient`:

    Now, you can create a table with a vector field `text_vec` and a full-text index on the `text` column.

    Sample code:

    ```python
    from pytidb.schema import TableModel, Field
    from pytidb.datatype import Text

    class Chunk(TableModel, table=True):
        id: int = Field(primary_key=True)
        text: str = Field(sa_type=Text)
        text_vec: list[float] = VectorField(dimension=3)

    table = db.create_table(schema=Chunk)
    table.create_fts_index("text")
    ```

### Step 2. Insert some sample data

=== "Python"

    Using `bulk_insert()` method to insert some sample data into the table.

    ```python
    table.bulk_insert([
        Chunk(
            text="TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads.",
            text_vec=[0.1, 0.2, 0.3]
        ),
        Chunk(
            text="PyTiDB is a Python library for developers to connect to TiDB.",
            text_vec=[0.4, 0.5, 0.6]
        ),
        Chunk(
            text="LlamaIndex is a Python library for building AI-powered applications.",
            text_vec=[0.7, 0.8, 0.9]
        ),
    ])
    ```

### Step 3. Define a reranker

In this example, we will use Jina AI reranker to rerank the hybrid search results, you can go to [Jina AI](https://jina.ai/) to get your own API key.

=== "Python"

    Define a reranker to rerank the hybrid search results.

    ```python
    from pytidb.rerankers import Reranker

    jinaai = Reranker(
        model_name="jina_ai/jina-reranker-m0",
        api_key="your-jina-api-key"
    )
    ```

To learn more about rerankers, please refer to the [reranking](./reranking.md) guide.

### Step 4. Perform hybrid search

To enable hybrid search, you need to set the `search_type` parameter to `hybrid` when calling the `search()` method.

```python
res = (
    table.search(
        "A library for my artificial intelligence software", search_type="hybrid"
    )
    .rerank(jinaai, "text")  # Rerank the result set with Jina AI reranker.
    .limit(3)
    .to_list()
)
res
```

The search results contains three special fields:

- `_distance`: The distance between the query vector and the vector data in the table returned by the vector search.
- `_match_score`: The match score between the query and the text field returned by the full-text search.
- `_score`: The final score of the search result, which is calculated by the reranker.

```json title="Output"
[
    {
        "id": 1,
        "text": "TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads.",
        "text_vec": [0.1, 0.2, 0.3],
        "_distance": 0.12,
        "_match_score": 0.88,
        "_score": 0.76
    },
    {
        "id": 2,
        "text": "PyTiDB is a Python library for developers to connect to TiDB.",
        "text_vec": [0.4, 0.5, 0.6],
        "_distance": 0.23,
        "_match_score": 0.67,
        "_score": 0.54
    },
    {
        "id": 3,
        "text": "LlamaIndex is a Python library for building AI-powered applications.",
        "text_vec": [0.7, 0.8, 0.9],
        "_distance": 0.35,
        "_match_score": 0.45,
        "_score": 0.32
    },
]
```
