<h1 align="center">TiDB Python AI SDK</h1>

<div align="center">

[![Python Package Index](https://img.shields.io/pypi/v/pytidb.svg)](https://pypi.org/project/pytidb)
[![Monthly PyPI Downloads](https://static.pepy.tech/badge/pytidb/month)](https://pepy.tech/projects/pytidb)
[![Total PyPI Downloads](https://static.pepy.tech/badge/pytidb)](https://pepy.tech/projects/pytidb)

</div>

<h4 align="center">
  <a href="https://github.com/pingcap/pytidb/blob/main/docs/quickstart.ipynb">Quick Start</a>
  •
  <a href="https://pingcap.github.io/ai/">Documentation</a>
  •
  <a href="https://pingcap.github.io/ai/examples/">Examples</a>
  •
  <a href="https://github.com/orgs/pingcap/projects/69/views/4">Roadmap</a>
  •
  <a href="https://discord.com/invite/vYU9h56kAX">Discord</a>
  •
  <a href="https://github.com/pingcap/pytidb/issues">Report Bug</a>
</h4>

## Introduction

**Python SDK for TiDB AI**: A unified data platform empowering developers to build next-generation AI applications.

- 🔍 **Unified Search Modes**: Vector · Full‑Text · Hybrid
- 🎭 **Auto‑Embedding & Multi‑Modal Storage**: Support for text, images, and more 
- 🖼️ **Image Search Support**: Text‑to‑image and image‑to‑image retrieval capabilities 
- 🎯 **Advanced Filtering & Reranking**: Flexible filters with optional reranker models to fine-tune result relevance 
- 💱 **Transaction Support**: Full transaction management including commit/rollback to ensure consistency 

## Installation

> [!NOTE]
> This Python package is under rapid development and its API may change. It is recommended to use a **fixed version** when installing, e.g., `pytidb==0.0.12`.

```bash
pip install pytidb

# To use built-in embedding functions and rerankers:
pip install "pytidb[models]"

# To convert query results to pandas DataFrame:
pip install pandas
```


## Connect to TiDB Cloud

Create a free TiDB cluster at [tidbcloud.com](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme).

```python
import os
from pytidb import TiDBClient

tidb_client = TiDBClient.connect(
    host=os.getenv("TIDB_HOST"),
    port=int(os.getenv("TIDB_PORT")),
    username=os.getenv("TIDB_USERNAME"),
    password=os.getenv("TIDB_PASSWORD"),
    database=os.getenv("TIDB_DATABASE"),
    ensure_db=True,
)
```

## Highlights

### 🤖 Automatic Embedding

PyTiDB automatically embeds text fields (e.g., `text`) and stores the vector embedding in a vector field (e.g., `text_vec`).

**Create a table with an embedding function:**

```python
from pytidb.schema import TableModel, Field, FullTextField
from pytidb.embeddings import EmbeddingFunction

# Set API key for embedding provider.
tidb_client.configure_embedding_provider("openai", api_key=os.getenv("OPENAI_API_KEY"))

class Chunk(TableModel):
    __tablename__ = "chunks"

    id: int = Field(primary_key=True)
    text: str = FullTextField()
    text_vec: list[float] = EmbeddingFunction(
        "openai/text-embedding-3-small"
    ).VectorField(source_field="text")  # 👈 Defines the vector field.
    user_id: int = Field()

table = tidb_client.create_table(schema=Chunk, if_exists="skip")
```

**Bulk insert data:**

```python
table.bulk_insert([
    Chunk(id=2, text="bar", user_id=2),   # 👈 The text field is embedded and saved to text_vec automatically.
    Chunk(id=3, text="baz", user_id=3),
    Chunk(id=4, text="qux", user_id=4),
])
```

### 🔍 Search

**Vector Search**

Vector search finds the most relevant records based on **semantic similarity**, so you don't need to include all keywords explicitly in your query.

```python
df = (
  table.search("<query>")  # 👈 The query is embedded automatically.
    .filter({"user_id": 2})
    .limit(2)
    .to_list()
)
# Output: A list of dicts.
```

See the [Vector Search example](https://github.com/pingcap/pytidb/blob/main/examples/vector_search) for more details.

**Full-text Search**

Full-text search tokenizes the query and finds the most relevant records by matching exact keywords.

```python
df = (
  table.search("<query>", search_type="fulltext")
    .limit(2)
    .to_pydantic()
)
# Output: A list of pydantic model instances.
```

See the [Full-text Search example](https://github.com/pingcap/pytidb/blob/main/examples/fulltext_search) for more details.

**Hybrid Search**

Hybrid search combines **exact matching** from full-text search with **semantic understanding** from vector search, delivering more relevant and reliable results.

```python
df = (
  table.search("<query>", search_type="hybrid")
    .limit(2)
    .to_pandas()
)
# Output: A pandas DataFrame.
```

See the [Hybrid Search example](https://github.com/pingcap/pytidb/blob/main/examples/hybrid_search) for more details.

**Image Search**

Image search lets you find visually similar images using natural language descriptions or another image as a reference.

```python
from PIL import Image
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction

# Define a multi-modal embedding model.
jina_embed_fn = EmbeddingFunction("jina_ai/jina-embeddings-v4")  # Using multi-modal embedding model.

class Pet(TableModel):
    __tablename__ = "pets"
    id: int = Field(primary_key=True)
    image_uri: str = Field()
    image_vec: list[float] = jina_embed_fn.VectorField(
        source_field="image_uri",
        source_type="image"
    )

table = tidb_client.create_table(schema=Pet, if_exists="skip")

# Insert sample images ...
table.insert(Pet(image_uri="path/to/shiba_inu_14.jpg"))

# Search for images using natural language
results = table.search("shiba inu dog").limit(1).to_list()

# Search for images using an image ...
query_image = Image.open("shiba_inu_15.jpg")
results = table.search(query_image).limit(1).to_pydantic()
```

See the [Image Search example](https://github.com/pingcap/pytidb/blob/main/examples/image_search) for more details.

#### Advanced Filtering

PyTiDB supports a variety of operators for flexible filtering:

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

### ⛓ Join Structured and Unstructured Data

```python
from pytidb import Session
from pytidb.sql import select

# Create a table to store user data:
class User(TableModel):
    __tablename__ = "users"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=20)

# Use the db_engine from TiDBClient when creating a Session
with Session(tidb_client.db_engine) as session:
    query = (
        select(Chunk).join(User, Chunk.user_id == User.id).where(User.name == "Alice")
    )
    chunks = session.exec(query).all()

[(c.id, c.text, c.user_id) for c in chunks]
```

### 💱 Transaction Support

PyTiDB supports transaction management, helping you avoid race conditions and ensure data consistency.

```python
with tidb_client.session() as session:
    initial_total_balance = tidb_client.query("SELECT SUM(balance) FROM players").scalar()

    # Transfer 10 coins from player 1 to player 2
    tidb_client.execute("UPDATE players SET balance = balance - 10 WHERE id = 1")
    tidb_client.execute("UPDATE players SET balance = balance + 10 WHERE id = 2")

    session.commit()
    # or session.rollback()

    final_total_balance = tidb_client.query("SELECT SUM(balance) FROM players").scalar()
    assert final_total_balance == initial_total_balance
```


## Asyncio Support (Python 3.10+)

PyTiDB now supports asyncio for non-blocking database operations!

### Basic Async Usage

```python
import asyncio
from pytidb import AsyncTiDBClient

async def main():
    # Connect using async context manager
    async with AsyncTiDBClient.connect(
        host="localhost",
        port=4000,
        username="root",
        database="test"
    ) as client:
        # Execute queries asynchronously
        result = await client.execute("INSERT INTO users VALUES (1, 'Alice')")
        print(f"Rows affected: {result.rowcount}")

        # Query data
        query_result = await client.query("SELECT * FROM users")
        users = query_result.to_list()
        print(f"Found {len(users)} users")

# Run the async function
asyncio.run(main())
```

### Async Table Operations

```python
import asyncio
from pytidb import AsyncTiDBClient
from pytidb.schema import TableModel, Field

class User(TableModel):
    __tablename__ = "users"
    id: int = Field(primary_key=True)
    name: str = Field(max_length=100)

async def main():
    async with AsyncTiDBClient.connect(
        host="localhost", port=4000, username="root", database="test"
    ) as client:
        # Create table
        table = await client.create_table(schema=User, if_exists="skip")

        # Insert records
        user = await table.insert({"id": 1, "name": "Alice"})
        print(f"Created user: {user.name}")

        # Query records
        result = await table.query()
        users = result.to_list()
        print(f"Found {len(users)} users")

asyncio.run(main())
```

### Concurrent Operations

The async API shines when performing concurrent operations:

```python
async def insert_many_users(client, users_data):
    table = await client.open_table("users")
    tasks = [table.insert(user) for user in users_data]
    results = await asyncio.gather(*tasks)
    return results

# Insert multiple users concurrently (much faster!)
users_data = [{"id": i, "name": f"User{i}"} for i in range(100)]
await insert_many_users(client, users_data)
```

### Key Features

- **Non-blocking operations**: All database operations run in thread pool
- **Async context managers**: Automatic connection cleanup with `async with`
- **Same API as sync version**: Easy to migrate existing code
- **Concurrent operations**: Use `asyncio.gather()` for parallel database operations
- **Full feature parity**: All TiDBClient and Table methods available

### API Reference

**AsyncTiDBClient Methods:**
- `connect()` - Create async connection
- `execute()` - Execute SQL statements
- `query()` - Execute SQL queries
- `create_table()` - Create tables
- `list_tables()` - List all tables
- `create_database()` - Create databases

**AsyncTable Methods:**
- `insert()` - Insert a record
- `bulk_insert()` - Insert multiple records
- `query()` - Query with filters
- `update()` - Update records
- `delete()` - Delete records
- `search()` - Vector/fulltext/hybrid search

### Backward Compatibility

The async API is completely separate from the sync API. Existing synchronous code continues to work without any changes.

See `examples/async_basic_example.py` for a complete example.


## Extensions


- 🔌 [Built-in MCP support](https://pingcap.github.io/ai/integrations/mcp)

> [!TIP]
> Click the button below to install **TiDB MCP Server** in Cursor. Then, confirm by clicking **Install** when prompted.
>
> [![Install TiDB MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=TiDB&config=eyJjb21tYW5kIjoidXZ4IC0tZnJvbSBweXRpZGJbbWNwXSB0aWRiLW1jcC1zZXJ2ZXIiLCJlbnYiOnsiVElEQl9IT1NUIjoibG9jYWxob3N0IiwiVElEQl9QT1JUIjoiNDAwMCIsIlRJREJfVVNFUk5BTUUiOiJyb290IiwiVElEQl9QQVNTV09SRCI6IiIsIlRJREJfREFUQUJBU0UiOiJ0ZXN0In19)
