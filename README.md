# TiDB Python SDK

<p>
  <a href="https://pypi.org/project/pytidb">
    <img src="https://img.shields.io/pypi/v/pytidb.svg" alt="Python Package Index"/>
  </a>
  <a href="https://pypistats.org/packages/pytidb">
    <img src="https://img.shields.io/pypi/dm/pytidb.svg" alt="Downloads"/>
  </a>
</p>

**Python SDK for TiDB AI**: A unified data platform empowering developers to build next-generation AI applications.

- 🔍 Multiple search modes: vector, full-text, and hybrid search
- 🎭 Multi-modal storage and processing: text, images, and more
- 🔄 Automatic embedding generation for text and images
- 🖼️ Image search: text-to-image and image-to-image capabilities
- 🎯 Advanced filtering capabilities
- 🥇 Reranker for search result tuning
- 💱 Transaction support
- 🔌 [Built-in MCP support](https://pingcap.github.io/ai/integrations/mcp)

**Documentation:** https://pingcap.github.io/ai/

**Quick Start:** [Jupyter Notebook](https://github.com/pingcap/pytidb/blob/main/docs/quickstart.ipynb)

> [!TIP]
> Click the button below to install **TiDB MCP Server** in Cursor. Then, confirm by clicking **Install** when prompted.
> 
> [![Install TiDB MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/install-mcp?name=TiDB&config=eyJjb21tYW5kIjoidXZ4IC0tZnJvbSBweXRpZGJbbWNwXSB0aWRiLW1jcC1zZXJ2ZXIiLCJlbnYiOnsiVElEQl9IT1NUIjoibG9jYWxob3N0IiwiVElEQl9QT1JUIjoiNDAwMCIsIlRJREJfVVNFUk5BTUUiOiJyb290IiwiVElEQl9QQVNTV09SRCI6IiIsIlRJREJfREFUQUJBU0UiOiJ0ZXN0In19)

## Installation

```bash
pip install pytidb

# To use built-in embedding functions and rerankers:
pip install "pytidb[models]"

# To convert query results to pandas DataFrame:
pip install pandas
```

> [!NOTE]
> This Python package is under active development and its API may change. It is recommended to use a fixed version when installing, e.g., `pytidb==0.0.8.post2`.

## Connect to TiDB Cloud

Create a free TiDB cluster at [tidbcloud.com](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme).

```python
import os
from pytidb import TiDBClient

db = TiDBClient.connect(
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

text_embed = EmbeddingFunction("openai/text-embedding-3-small")

class Chunk(TableModel):
    __tablename__ = "chunks"

    id: int = Field(primary_key=True)
    text: str = FullTextField()
    text_vec: list[float] = text_embed.VectorField(
        source_field="text"
    )  # 👈 Defines the vector field.
    user_id: int = Field()

table = db.create_table(schema=Chunk, mode="exist_ok")
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

table = db.create_table(schema=Pet, mode="exist_ok")

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

with Session(engine) as session:
    query = (
        select(Chunk).join(User, Chunk.user_id == User.id).where(User.name == "Alice")
    )
    chunks = session.exec(query).all()

[(c.id, c.text, c.user_id) for c in chunks]
```

### 💱 Transaction Support

PyTiDB supports transaction management, helping you avoid race conditions and ensure data consistency.

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

## Getting Help

- 💬 Join our Discord: [TiDB Community](https://discord.com/invite/vYU9h56kAX)
- 🐛 Report issues or request features: [Open an issue](https://github.com/pingcap/pytidb/issues)
- 📝 Contact sales or get enterprise support: [PingCAP Contact Form](https://www.pingcap.com/contact-us/)
