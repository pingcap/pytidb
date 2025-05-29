import json
import os
import dotenv

from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field
from pytidb.datatype import Text

dotenv.load_dotenv()


# Connect to TiDB.
print("=== CONNECT TO TIDB ===")
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)
print("Connected to TiDB.\n")


# Create embedding function.
embed_fn = EmbeddingFunction(
    model_name="openai/text-embedding-3-small",
    api_key=os.getenv("OPENAI_API_KEY"),
)


# Create a table with a text field and a vector field.
print("=== CREATE TABLE ===")


class Chunk(TableModel, table=True):
    __tablename__ = "chunks_for_hybrid_search"
    id: int = Field(primary_key=True)
    text: str = Field(sa_type=Text)
    text_vec: list[float] = embed_fn.VectorField(source_field="text")


table = db.create_table(schema=Chunk)

if not table.has_fts_index("text"):
    table.create_fts_index("text")

print("Table created.\n")


# Insert some sample data.
print("=== INSERT SAMPLE DATA ===")
table.delete()
# table.truncate()
table.bulk_insert(
    [
        Chunk(
            text="TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads.",
        ),
        Chunk(
            text="PyTiDB is a Python library for developers to connect to TiDB.",
        ),
        Chunk(
            text="LlamaIndex is a Python library for building AI-powered applications.",
        ),
    ]
)
print("Inserted 3 rows.\n")


# Perform hybrid search.
print("=== PERFORM HYBRID SEARCH ===")
results = table.search("AI database", search_type="hybrid").limit(3).to_list()

print("Search results:")
for item in results:
    item.pop("text_vec")
print(json.dumps(results, indent=4, sort_keys=True))
