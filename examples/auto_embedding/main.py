import os
import dotenv
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field
from pytidb.datatype import TEXT
from pytidb import TiDBClient

# Load environment variables
dotenv.load_dotenv()

# Connect to database with connection parameters
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)

# Define embedding function
print("=== Define embedding function ===")
embed_func = EmbeddingFunction(
    model_name="jina_ai/jina-embeddings-v3",
    api_key=os.getenv("JINA_AI_API_KEY"),
)
print("Embedding function defined")

# Define table schema
print("\n=== Define table schema ===")


class Chunk(TableModel):
    id: int = Field(primary_key=True)
    text: str = Field(sa_type=TEXT)
    text_vec: list[float] = embed_func.VectorField(source_field="text")


table = db.create_table(schema=Chunk, mode="overwrite")
print("Table created")

# Truncate table
print("\n=== Truncate table ===")
table.truncate()
print("Table truncated")

# Insert sample data
print("\n=== Insert sample data ===")
table.bulk_insert(
    [
        # 👇 The text will be embedded and the vector field will be populated automatically.
        Chunk(
            text="TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads."
        ),
        Chunk(text="PyTiDB is a Python library for developers to connect to TiDB."),
        Chunk(
            text="LlamaIndex is a Python library for building AI-powered applications."
        ),
    ]
)
print("Inserted 3 chunks")

# Perform vector search
print("\n=== Perform vector search ===")
results = (
    table.search("HTAP database").limit(3).to_list()
)  # 👈 The query text will be embedded automatically.
for item in results:
    print(f"id: {item['id']}, text: {item['text']}, distance: {item['_distance']}")
