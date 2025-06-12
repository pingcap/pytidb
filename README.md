# TiDB Python SDK

> [!NOTE]
> This Python package is under rapid development and the API is subject to change, it is recommended to use a fixed version when importing, e.g. `pytidb==0.0.6`

<p>
  <a href="https://pypi.org/project/pytidb">
    <img src="https://img.shields.io/pypi/v/pytidb.svg" alt="Python Package Index"/>
  </a>
  <a href="https://pypistats.org/packages/pytidb">
    <img src="https://img.shields.io/pypi/dm/pytidb.svg" alt="Downloads"/>
  </a>
</p>

Python SDK for TiDB AI: A unified data platform designed to empower developers in building next-generation AI applications.

- 🔍 Support various search modes: vector search, fulltext search, hybrid search
- 🔄 Automatic embedding generation
- 🎯 Advanced filtering capabilities
- 🥇 Tuning search results with Reranker
- 💱 Transaction support

Documentation: https://pingcap.github.io/ai/

Quick Start Guide: [Jupyter Notebook](https://github.com/pingcap/pytidb/blob/main/docs/quickstart.ipynb)

Install TiDB MCP Server (Docs: https://pingcap.github.io/ai/integrations/mcp): 

[![Install TiDB MCP Server](https://cursor.com/deeplink/mcp-install-light.svg)](https://cursor.com/install-mcp?name=TiDB&config=eyJjb21tYW5kIjoidXZ4IC0tZnJvbSBweXRpZGJbbWNwXSB0aWRiLW1jcC1zZXJ2ZXIiLCJlbnYiOnsiVElEQl9IT1NUIjoibG9jYWxob3N0IiwiVElEQl9QT1JUIjoiNDAwMCIsIlRJREJfVVNFUk5BTUUiOiJyb290IiwiVElEQl9QQVNTV09SRCI6IiIsIlRJREJfREFUQUJBU0UiOiJ0ZXN0In19)

## Installation

```bash
pip install pytidb

# If you want to use built-in embedding function and rerankers.
pip install "pytidb[models]"

# If you want to convert query result to pandas DataFrame.
pip install pandas
```

## Connect to TiDB Cloud

Go to [tidbcloud.com](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme) to create a free TiDB cluster.

```python
import os
from pytidb import TiDBClient

db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST"),
    port=int(os.getenv("TIDB_PORT")),
    username=os.getenv("TIDB_USERNAME"),
    password=os.getenv("TIDB_PASSWORD"),
    database=os.getenv("TIDB_DATABASE"),
)
```

## Highlights

### 🤖 Auto Embedding

PyTiDB automatically embeds the text field (e.g. `text`) and saves the vector embedding to the vector field (e.g. `text_vec`).

**Create a table with embedding function**:

```python
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction

text_embed = EmbeddingFunction("openai/text-embedding-3-small")

class Chunk(TableModel, table=True):
    __tablename__ = "chunks"

    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: list[float] = text_embed.VectorField(
        source_field="text"
    )  # 👈 Define the vector field.
    user_id: int = Field()

table = db.create_table(schema=Chunk)
```

**Bulk insert data**:

```python
table.bulk_insert(
    [
        Chunk(id=2, text="bar", user_id=2),   # 👈 The text field will be embedded to a 
        Chunk(id=3, text="baz", user_id=3),   # vector and save to the text_vec field
        Chunk(id=4, text="qux", user_id=4),   # automatically.
    ]
)
```

### 🔍 Search

**Vector Search**

Vector search help you find the most relevant records based on **semantic similarity**, so you don't need to explicitly include all the keywords in your query.

```python
df = (
  table.search("<query>")  # 👈 The query will be embedding automatically.
    .filter({"user_id": 2})
    .limit(2)
    .to_pandas()
)
```

For a complete example, please go to the [Vector Search](https://github.com/pingcap/pytidb/blob/main/examples/vector_search) demo.

**Fulltext Search**

Full-text search helps tokenize the query and find the most relevant records by matching exact keywords.

```python
if not table.has_fts_index("text"):
    table.create_fts_index("text")   # 👈 Create a fulltext index on the text column.

df = (
  table.search("<query>", search_type="fulltext")
    .limit(2)
    .to_pandas()
)
```

For a complete example, please go to the [Fulltext Search](https://github.com/pingcap/pytidb/blob/main/examples/fulltext_search) demo.

**Hybrid Search**

Hybrid search combines vector search and fulltext search to provide a more accurate and relevant search result.

```python
from pytidb.rerankers import Reranker

jinaai = Reranker(model_name="jina_ai/jina-reranker-m0")

df = (
  table.search("<query>", search_type="hybrid")
    .rerank(jinaai, "text")  # 👈 Rerank the query result with the jinaai model.
    .limit(2)
    .to_pandas()
)
```

For a complete example, please go to the [Hybrid Search](https://github.com/pingcap/pytidb/blob/main/examples/hybrid_search) demo.

#### Advanced Filtering

PyTiDB supports various operators for flexible filtering:

| Operator | Description           | Example                                    |
| -------- | --------------------- | ------------------------------------------ |
| `$eq`    | Equal to              | `{"field": {"$eq": "hello"}}`              |
| `$gt`    | Greater than          | `{"field": {"$gt": 1}}`                    |
| `$gte`   | Greater than or equal | `{"field": {"$gte": 1}}`                   |
| `$lt`    | Less than             | `{"field": {"$lt": 1}}`                    |
| `$lte`   | Less than or equal    | `{"field": {"$lte": 1}}`                   |
| `$in`    | In array              | `{"field": {"$in": [1, 2, 3]}}`            |
| `$nin`   | Not in array          | `{"field": {"$nin": [1, 2, 3]}}`           |
| `$and`   | Logical AND           | `{"$and": [{"field1": 1}, {"field2": 2}]}` |
| `$or`    | Logical OR            | `{"$or": [{"field1": 1}, {"field2": 2}]}`  |


### ⛓ Join Structured Data and Unstructured Data

```python
from pytidb import Session
from pytidb.sql import select

# Create a table to store user data:
class User(TableModel, table=True):
    __tablename__ = "users"

    id: int = Field(primary_key=True)
    name: str = Field(max_length=20)


with Session(engine) as session:
    query = (
        select(Chunk).join(User, Chunk.user_id == User.id).where(User.name == "Alice")
    )
    chunks = session.exec(query).all()

[(c.id, c.text, c.user_id) for c in chunks]
```

### 💱Transaction Support

PyTiDB supports transaction management, so you can avoid race conditions and ensure data consistency.

```python
with db.session() as session:
    initial_total_balance = db.query("SELECT SUM(balance) FROM players").scalar()

    # Transfer 10 coins from player 1 to player 2
    db.execute("UPDATE players SET balance = balance - 10 WHERE id = 1")
    db.execute("UPDATE players SET balance = balance + 10 WHERE id = 2")

    session.commit()
    # or session.rollback()

    final_total_balance = db.query("SELECT SUM(balance) FROM players").scalar()
    assert final_total_balance == initial_total_balance
```
