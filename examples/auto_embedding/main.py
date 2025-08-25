import os
import dotenv
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel, Field
from pytidb.datatype import TEXT
from pytidb import TiDBClient

# Load environment variables
dotenv.load_dotenv()

# Connect to database with connection parameters
tidb_client = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "pytidb_auto_embedding"),
    ensure_db=True,
)

# Define embedding function
print("=== Define embedding function ===")

provider = os.getenv("EMBEDDING_PROVIDER", "tidbcloud_free")
if provider == "tidbcloud_free":
    embed_func = EmbeddingFunction(
        model_name="tidbcloud_free/amazon/titan-embed-text-v2",
    )
elif provider == "openai":
    tidb_client.configure_embedding_provider(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    embed_func = EmbeddingFunction(
        model_name="openai/text-embedding-3-small",
    )
elif provider == "jina_ai":
    tidb_client.configure_embedding_provider(
        provider="jina_ai",
        api_key=os.getenv("JINA_AI_API_KEY"),
    )
    embed_func = EmbeddingFunction(
        model_name="jina_ai/jina-embeddings-v3",
    )
elif provider == "cohere":
    tidb_client.configure_embedding_provider(
        provider="cohere",
        api_key=os.getenv("COHERE_API_KEY"),
        use_server=True,
    )
    embed_func = EmbeddingFunction(
        model_name="cohere/embed-v4.0",
        dimensions=1536,
        use_server=True,
    )
elif provider == "huggingface":
    tidb_client.configure_embedding_provider(
        provider="huggingface",
        api_key=os.getenv("HUGGINGFACE_API_KEY"),
    )
    embed_func = EmbeddingFunction(
        model_name="huggingface/sentence-transformers/all-MiniLM-L6-v2",
        dimensions=384,
        use_server=True,
    )
elif provider == "nvidia_nim":
    tidb_client.configure_embedding_provider(
        provider="nvidia_nim",
        api_key=os.getenv("NVIDIA_NIM_API_KEY"),
    )
    embed_func = EmbeddingFunction(
        model_name="nvidia_nim/baai/bge-m3",
        dimensions=1024,
        use_server=True,
    )
elif provider == "gemini":
    tidb_client.configure_embedding_provider(
        provider="gemini",
        api_key=os.getenv("GEMINI_API_KEY"),
    )
    embed_func = EmbeddingFunction(
        model_name="gemini/gemini-embedding-001",
        dimensions=3072,
        use_server=True,
    )
else:
    raise ValueError(f"Invalid embedding provider: {provider}")

print(f"Embedding function (model id: {embed_func.model_name}) defined")

# Define table schema
print("\n=== Define table schema ===")


class Chunk(TableModel):
    id: int = Field(primary_key=True)
    text: str = Field(sa_type=TEXT)
    text_vec: list[float] = embed_func.VectorField(source_field="text")


table = tidb_client.create_table(schema=Chunk, if_exists="overwrite")
print("Vector table created")

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
