# TiDB Python SDK

Python SDK for vector storage and retrieval operations with TiDB.

- 🔄 Automatic embedding generation
- 🔍 Vector similarity search
- 🎯 Advanced filtering capabilities
- 📦 Bulk operations support

Documentation: [Jypyter Notebook](docs/quickstart.ipynb)

## Installation

```bash
pip install pytidb
```

## Highlights

### 🤖 Auto Embedding

```python
text_embed = EmbeddingFunction("openai/text-embedding-3-small")

class Chunk(TableModel, table=True):
    __tablename__ = "chunks"
    __table_args__ = {"extend_existing": True}

    id: int = Field(primary_key=True)
    text: str = Field()
    text_vec: Optional[Any] = text_embed.VectorField(
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
from sqlmodel import select, Session

# Create a table to stored user data:
class User(TableModel, table=True):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

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
