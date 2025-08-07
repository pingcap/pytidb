# Custom Embedding Function with BGE-M3

This example demonstrates how to create and use a custom embedding function with PyTiDB using the BGE-M3 model.

* Create a custom embedding function by inheriting from `BaseEmbeddingFunction`
* Integrate BGE-M3 model for high-quality text embeddings
* Use the custom embedding function for automatic vector generation
* Perform semantic search with the embedded vectors

## Features

- **BGE-M3 Integration**: Uses the powerful BGE-M3 model for text embeddings
- **Custom Implementation**: Shows how to build your own embedding function
- **Automatic Embedding**: Vectors are generated automatically when inserting data
- **Batch Processing**: Efficient batch embedding for multiple documents
- **Semantic Search**: Demonstrates vector search capabilities

## Prerequisites

- **Python 3.10+**
- **A TiDB Cloud Serverless cluster**: Create a free cluster here: [tidbcloud.com ↗️](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme)
- **Sufficient GPU memory** (recommended): BGE-M3 benefits from GPU acceleration

### Performance Notes

- **First Run**: Model download and loading may take a few minutes
- **GPU Acceleration**: BGE-M3 will automatically use GPU if available
- **Memory Usage**: BGE-M3 requires ~2GB GPU memory or ~4GB RAM
- **Batch Size**: Larger batches improve throughput but require more memory

## How to run

**Step 1**: Clone the repository

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/custom_embedding_function/
```

**Step 2**: Install the required packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step 3**: Set up environment to connect to database

Go to [TiDB Cloud console](https://tidbcloud.com/clusters) to get the connection parameters and set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST={gateway-region}.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USERNAME={prefix}.root
TIDB_PASSWORD={password}
TIDB_DATABASE=test
EOF
```

**Step 4**: Run the demo

```bash
python main.py
```

**Expected output:**

```plain
=== Connecting to TiDB ===
Connected to TiDB successfully

=== Initializing BGE-M3 Embedding Function ===
Loading BGE-M3 model: BAAI/bge-m3
BGE-M3 model loaded with 1024 dimensions

=== Defining Table Schema ===
Table created with BGE-M3 vector field

=== Inserting Sample Documents ===
Inserted 5 documents with auto-generated embeddings

=== Performing Vector Search ===

Query 1: 'What is a distributed database?'
Results:
  1. [TiDB Introduction] (distance: 0.3243)
     Content: TiDB is a distributed SQL database that supports both OLTP and OLAP work...
  2. [Vector Databases] (distance: 0.4567)
     Content: Vector databases are specialized databases designed to store and query hi...
  3. [Machine Learning] (distance: 0.6234)
     Content: Machine learning is a subset of artificial intelligence that enables com...

Query 2: 'How do embedding models work?'
Results:
  1. [BGE-M3 Model] (distance: 0.2891)
     Content: BGE-M3 is a versatile embedding model that supports dense retrieval, spa...
  2. [Neural Networks] (distance: 0.4123)
     Content: Neural networks are computing systems inspired by biological neural netw...
  3. [Machine Learning] (distance: 0.4567)
     Content: Machine learning is a subset of artificial intelligence that enables com...

=== Manual Embedding Usage ===
Query: 'How can I use TiDB for AI applications?'
Embedding dimensions: 1024
First 5 embedding values: [0.123, -0.456, 0.789, -0.234, 0.567]

Batch processed 3 texts:
  Text 1: 1024 dimensions
    Content: 'Artificial intelligence and machine learning'
  Text 2: 1024 dimensions
    Content: 'Database systems and data storage'
  Text 3: 1024 dimensions
    Content: 'Information retrieval and search engines'

=== Demo Completed Successfully ===
This demonstrates how to use a custom BGE-M3 embedding function with PyTiDB
for automatic embedding generation and vector search capabilities.
```

## Understanding the Code

### Custom Embedding Function

The `BGEM3EmbeddingFunction` class inherits from `BaseEmbeddingFunction` and implements the required abstract methods:

```python
class BGEM3EmbeddingFunction(BaseEmbeddingFunction):
    def get_query_embedding(self, query, source_type="text", **kwargs) -> List[float]:
        # Convert query to embedding using BGE-M3
        
    def get_source_embedding(self, source, source_type="text", **kwargs) -> List[float]:
        # Convert source data to embedding
        
    def get_source_embeddings(self, sources, source_type="text", **kwargs) -> List[List[float]]:
        # Batch process multiple sources
```

### Key Features

1. **Lazy Loading**: The BGE-M3 model is loaded only when first needed
2. **FP16 Support**: Uses half-precision for faster inference
3. **Batch Processing**: Efficiently handles multiple texts at once
4. **Error Handling**: Proper error messages for missing dependencies

### Table Schema

```python
class Document(TableModel):
    id: int = Field(primary_key=True)
    content: str = Field(sa_type=Text)
    # Automatic embedding field
    content_vec: list[float] = embed_func.VectorField(source_field="content")
```

## GPU Memory Issues

If you run out of GPU memory, disable FP16 or force CPU usage:

```python
embed_func = BGEM3EmbeddingFunction(
    use_fp16=False,  # Disable FP16
    device="cpu"     # Force CPU usage
)
```

## Next Steps

- Trying to use [Retrieval-Augmented Generation (RAG)](/examples/rag/README.md) to give you a better context window for generating the answer.
- Trying to use [Full-text Search (FTS)](/examples/image_search/README.md) feature for boosting your callback rate of RAG.
- Trying to use [Text to SQL](/examples/text2sql/README.md) to achieve a natural language to SQL application.