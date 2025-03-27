# TiDB Python SDK

Python SDK for vector storage and retrieval operations with TiDB.

- 🔄 Automatic embedding generation
- 🔍 Vector similarity search
- 🎯 Advanced filtering capabilities
- 📦 Bulk operations support

Documentation: [Jupyter Notebook](docs/quickstart.ipynb)

## Installation

```bash
pip install pytidb
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
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: list[float] = text_embed.VectorField(
        source_field="text"
    )  # 👈 Define the vector field.
    user_id: int = Field()

table = db.create_table(schema=Chunk)
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

### ⛓ Join Structured Data and Unstructured Data

```python
from pytidb import Session
from pytidb.sql import select

# Create a table to stored user data:
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


### 💻 Execute or Query with Raw SQL

```python
db.execute("INSERT INTO chunks(text, user_id) VALUES ('inserted from raw sql', 5)")
```

```python
db.query("SELECT id, text, user_id FROM chunks LIMIT 5").to_pandas()
```
