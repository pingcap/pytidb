# TiDB Python SDK

Python SDK for vector storage and retrieval operations with TiDB.

- 🔄 Automatic embedding generation
- 🔍 Vector similarity search
- 🎯 Advanced filtering capabilities
- 📦 Bulk operations support
- 💱 Transaction support
- 🔌 [Model Context Protocol (MCP) support](https://github.com/pingcap/pytidb/blob/main/docs/mcp.md)

Documentation: [Jupyter Notebook](https://github.com/pingcap/pytidb/blob/main/docs/quickstart.ipynb)

## Installation

```bash
pip install pytidb

# If you want to use built-in embedding function.
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

### 🔍 Vector Search with Filtering

```python
table.search(
    "A quick fox in the park"
)  # 👈 The query will be embedding automatically.
.filter({"user_id": 2})
.limit(2)
.to_pandas()
```

#### Advanced Filtering

TiDB Client supports various filter operators for flexible querying:

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