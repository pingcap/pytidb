import os
import dotenv
from custom_embedding import BGEM3EmbeddingFunction
from pytidb.schema import TableModel, Field
from pytidb.datatype import TEXT
from pytidb import TiDBClient

# Load environment variables
dotenv.load_dotenv()

# Connect to database with connection parameters
print("=== Connecting to TiDB ===")
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "custom_embedding_example"),
    ensure_db=True,
)
print("Connected to TiDB successfully")

# Define custom BGE-M3 embedding function
print("\n=== Initializing BGE-M3 Embedding Function ===")
embed_func = BGEM3EmbeddingFunction()
print("BGE-M3 model loaded (1024 dimensions)")

# Define table schema with auto-embedding
print("\n=== Defining Table Schema ===")


class Document(TableModel):
    __tablename__ = "bge_m3_documents"

    id: int = Field(primary_key=True)
    title: str = Field(sa_type=TEXT)
    content: str = Field(sa_type=TEXT)
    # Auto-embedding field using our custom BGE-M3 function
    content_vec: list[float] = embed_func.VectorField(source_field="content")


# Create table
table = db.create_table(schema=Document, if_exists="overwrite")
print("Table created with BGE-M3 vector field")

# Insert sample documents
print("\n=== Inserting Sample Documents ===")
sample_docs = [
    Document(
        title="TiDB Introduction",
        content="TiDB is a distributed SQL database that supports both OLTP and OLAP workloads. It provides MySQL compatibility and horizontal scalability.",
    ),
    Document(
        title="BGE-M3 Model",
        content="BGE-M3 is a versatile embedding model that supports dense retrieval, sparse retrieval, and multi-vector retrieval for information retrieval tasks.",
    ),
    Document(
        title="Vector Databases",
        content="Vector databases are specialized databases designed to store and query high-dimensional vectors efficiently, enabling semantic search and AI applications.",
    ),
    Document(
        title="Machine Learning",
        content="Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed.",
    ),
    Document(
        title="Neural Networks",
        content="Neural networks are computing systems inspired by biological neural networks. They consist of layers of interconnected nodes that process information.",
    ),
]

# Insert documents (embeddings will be generated automatically)
table.bulk_insert(sample_docs)
print(f"Inserted {len(sample_docs)} documents with auto-generated embeddings")

# Demonstrate vector search
print("\n=== Performing Vector Search ===")
results = table.search("Is TiDB a distributed database?").limit(3).to_list()

print("Results:")
for result in results:
    print(f"  [{result['title']}] (distance: {result['_distance']:.4f})")
    print(f"     Content: {result['content'][:80]}...")

# Demonstrate manual embedding usage
print("\n=== Manual Embedding Usage ===")

# Get embedding for a custom query
custom_query = "How can I use TiDB for AI applications?"
query_embedding = embed_func.get_query_embedding(custom_query)

print(f"Query: '{custom_query}'")
print(f"Embedding dimensions: {len(query_embedding)}")
print(f"First 5 embedding values: {query_embedding[:5]}")

# Batch embedding example
batch_texts = [
    "Artificial intelligence and machine learning",
    "Database systems and data storage",
    "Information retrieval and search engines",
]

batch_embeddings = embed_func.get_source_embeddings(batch_texts)
print(f"\nBatch processed {len(batch_texts)} texts:")
for i, text in enumerate(batch_texts):
    print(f"  Text {i + 1}: {len(batch_embeddings[i])} dimensions")
    print(f"    Content: '{text}'")

print("\n=== Demo Completed Successfully ===")
print("This demonstrates how to use a custom BGE-M3 embedding function with PyTiDB")
print("for automatic embedding generation and vector search capabilities.")
