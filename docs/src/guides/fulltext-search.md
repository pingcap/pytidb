# Fulltext Search

Unlike [Vector Search](./vector-search.md), which focuses on semantic similarity, full-text search lets you retrieve documents for exact keywords. 

The full-text search feature in TiDB provides the following capabilities:

- **Query text data directly**: you can search any string columns directly without the embedding process.

- **Support for multiple languages**: no need to specify the language for high-quality search. TiDB supports documents in multiple languages stored in the same table and automatically chooses the best text analyzer for each document.

- **Order by relevance**: the search result can be ordered by relevance using the widely adopted BM25 ranking algorithm.

- **Fully compatible with SQL**: all SQL features, such as pre-filtering, post-filtering, grouping, and joining, can be used with full-text search.

!!! note

    Currently, full-text search is only available for the following product option and region:
    
    - **TiDB Cloud Serverless: Frankfurt (eu-central-1)**

## Basic Usage

Assume you have already [connected to your TiDB database](./connect.md) using `TiDBClient`.

Example:

```python hl_lines="9 10"
from pytidb.schema import TableModel, Field

class Document(TableModel, table=True):
    id: int = Field(primary_key=True)
    text: str

table = db.create_table(schema=Document)

table.create_fts_index("text")
table.search("library", search_type="fulltext").limit(3)
```
