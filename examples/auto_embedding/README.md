# Auto Embedding Demo

This example showcases how to use the auto embedding feature with PyTiDB Client.

* Connect to TiDB with PyTiDB Client
* Define a table with a VectorField configured for automatic embedding
* Insert plain text data, embeddings are populated automatically in the background
* Run vector searches with natural language queries, embedding happens transparently

## Prerequisites

- **Python 3.10+**
- **A TiDB Cloud Serverless cluster**: Create a free cluster here: [tidbcloud.com ↗️](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme)
- **Jina AI API key**: Go to [Jina AI](https://jina.ai/embeddings/) to get your own API key

## How to run

**Step 1**: Clone the repository

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/auto_embedding/
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
JINA_AI_API_KEY={your-jina-api-key}
EOF
```

**Step 4**: Run the demo

```bash
python main.py
```

**Expected output:**

```plain
=== Define embedding function ===
Embedding function defined

=== Define table schema ===
Table created

=== Truncate table ===
Table truncated

=== Insert sample data ===
Inserted 3 chunks

=== Perform vector search ===
id: 1, text: TiDB is a distributed database that supports OLTP, OLAP, HTAP and AI workloads., distance: 0.30373281240458805
id: 2, text: PyTiDB is a Python library for developers to connect to TiDB., distance: 0.422506501973434
id: 3, text: LlamaIndex is a Python library for building AI-powered applications., distance: 0.5267239638442787
```
