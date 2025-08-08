# Custom Embedding Function with BGE-M3

This example demonstrates how to create and use a custom embedding function with PyTiDB using the BGE-M3 model.

## What This Example Does

- Implements a custom embedding function by inheriting from BaseEmbeddingFunction
- Integrates the **BGE-M3** model to produce text embeddings in the custom BGEM3EmbeddingFunction (You can use any embedding model you prefer)
- Shows how to enable auto embedding feature using a custom embedding function
- Supports batch processing to embed multiple documents efficiently
- Demonstrates how to run semantic search queries on the stored vectors

## Prerequisites

- **Python 3.10+**  
- **A TiDB Cloud Serverless cluster**: Create a free cluster here: [tidbcloud.com ↗️](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme)  
- **Hardware requirements**:  
  - If GPU is available, BGE-M3 will use it automatically, requiring about **2GB GPU memory**  
  - To run on CPU (without GPU), you need to specify parameters manually; CPU mode requires about **4GB RAM**  

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

```

> [!NOTE]
> The model may take a few minutes to download and load the first time you run it.

**Expected output:**

```plain
=== Connecting to TiDB ===
Connected to TiDB successfully

=== Initializing BGE-M3 Embedding Function ===
Fetching 30 files: 100%|███████████████████████████████████████████████████████████████████████| 30/30 [00:00<00:00, 70611.18it/s]
BGE-M3 model loaded (1024 dimensions)

=== Defining Table Schema ===
Table created with BGE-M3 vector field

=== Inserting Sample Documents ===
Inserted 5 documents with auto-generated embeddings

=== Performing Vector Search ===
Results:
  [TiDB Introduction] (distance: 0.2263)
     Content: TiDB is a distributed SQL database that supports both OLTP and OLAP workloads. I...
  [Vector Databases] (distance: 0.5181)
     Content: Vector databases are specialized databases designed to store and query high-dime...
  [BGE-M3 Model] (distance: 0.6145)
     Content: BGE-M3 is a versatile embedding model that supports dense retrieval, sparse retr...

=== Manual Embedding Usage ===
Query: 'How can I use TiDB for AI applications?'
Embedding dimensions: 1024
First 5 embedding values: [-0.03271484375, -0.05279541015625, -0.031707763671875, 0.038299560546875, -0.0033550262451171875]

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

Then, instantiate the **BGEM3EmbeddingFunction**:

```python
from custom_embedding import BGEM3EmbeddingFunction

bge_m3 = BGEM3EmbeddingFunction(
    model_name='BAAI/bge-m3',  # The model will be download and load from HuggingFace Hub with the name.
    device='cpu', # Specify the device to use, e.g., 'cpu' or 'cuda:0'
    use_fp16=False # Specify whether to use half-precision for faster inference
)
```

To enable auto embedding for the custom **BGEM3EmbeddingFunction**, define the `VectorField` with it and specify the `source_field` parameter:

```python
class Document(TableModel):
    id: int = Field(primary_key=True)
    content: str = Field(sa_type=TEXT)
    content_vec: list[float] = bge_m3.VectorField(source_field="content")
```

## Troubleshooting

### GPU Memory Issues

If you run out of GPU memory, force CPU usage and disable FP16:

```python
embed_func = BGEM3EmbeddingFunction(
    use_fp16=False,  # Disable FP16
    device="cpu"     # Force CPU usage
)
```

## Next Steps

- Trying to use [Retrieval-Augmented Generation (RAG)](/examples/rag/README.md) to give you a better context window for generating the answer.
- Trying to use [Full-text Search (FTS)](/examples/image_search/README.md) feature for boosting the recall rate of RAG.
- Trying to use [Text to SQL](/examples/text2sql/README.md) to achieve a natural language to SQL application.