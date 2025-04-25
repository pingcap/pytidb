# TiDB Python SDK

<p>
  <a href="https://pypi.org/project/pytidb">
    <img src="https://img.shields.io/pypi/v/pytidb.svg" alt="Python Package Index"/>
  </a>
  <a href="https://pypistats.org/packages/pytidb">
    <img src="https://img.shields.io/pypi/dm/pytidb.svg" alt="Downloads"/>
  </a>
</p>

A Python SDK for TiDB developers to build AI applications efficiently.

- 🔍 Support various search modes: vector search, fulltext search, hybrid search
- 🔄 Automatic embedding generation
- 🎯 Advanced filtering capabilities
- 💱 Transaction support
- 🔌 [Model Context Protocol (MCP) support](https://github.com/pingcap/pytidb/blob/main/docs/mcp.md)

Documentation: [Jupyter Notebook](https://github.com/pingcap/pytidb/blob/main/docs/quickstart.ipynb)

## Installation

```bash
pip install pytidb

# If you want to use built-in embedding function and rerankers.
pip install "pytidb[models]"

# If you want to convert query result to pandas DataFrame.
pip install pandas
```

## Connect to TiDB

Go [tidbcloud.com](https://tidbcloud.com/) or using [tiup playground](https://docs.pingcap.com/tidb/stable/tiup-playground/) to create a free TiDB database cluster.

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

### 📦 Bulk operations support

```python
table.bulk_insert(
    [
        Chunk(id=2, text="bar", user_id=2),   # 👈 The text field will be embedded to a vector 
        Chunk(id=3, text="baz", user_id=3),   # and save to the text_vec field automatically.
        Chunk(id=4, text="qux", user_id=4),
    ]
)
```

### 🔍 Search

**Vector Search**:

Vector search help you find the most relevant records based on **semantic similarity**, so you don't need to explicitly include all the keywords in your query.

```python
df = (
  table.search("<query>")  # 👈 The query will be embedding automatically.
    .filter({"user_id": 2})
    .limit(2)
    .to_pandas()
)
```

**Fulltext Search**:

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

**Hybrid Search**:

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

#### Advanced Filtering

PyTiDB supports various operators for flexible filtering:

| Operator | Description               | Example                                      |
|----------|---------------------------|----------------------------------------------|
| `$eq`    | Equal to                  | `{"field": {"$eq": "hello"}}`                |
| `$gt`    | Greater than              | `{"field": {"$gt": 1}}`                      |
| `$gte`   | Greater than or equal     | `{"field": {"$gte": 1}}`                     |
| `$lt`    | Less than                 | `{"field": {"$lt": 1}}`                      |
| `$lte`   | Less than or equal        | `{"field": {"$lte": 1}}`                     |
| `$in`    | In array                  | `{"field": {"$in": [1, 2, 3]}}`              |
| `$nin`   | Not in array              | `{"field": {"$nin": [1, 2, 3]}}`             |
| `$and`   | Logical AND               | `{"$and": [{"field1": 1}, {"field2": 2}]}`   |
| `$or`    | Logical OR                | `{"$or": [{"field1": 1}, {"field2": 2}]}`    |


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

### 💱Transaction support

PyTiDB supports transaction management, so you can avoid race conditions and ensure data consistency.

```python
with db.session() as session:
    initial_total_balance = db.query("SELECT SUM(balance) FROM players").scalar()

    # Transfer 10 coins from player 1 to player 2
    db.execute("UPDATE players SET balance = balance + 10 WHERE id = 1")
    db.execute("UPDATE players SET balance = balance - 10 WHERE id = 2")

    session.commit()
    # or session.rollback()

    final_total_balance = db.query("SELECT SUM(balance) FROM players").scalar()
    assert final_total_balance == initial_total_balance
```
