# Auto Embedding Demo

This example demonstrates how to use auto embedding with PyTiDB.

* Use `pytidb` to connect to TiDB
* Perform auto embedding on data

## Prerequisites

* Python 3.8+
* TiDB server connection string (local or TiDB Cloud)
* Jina AI API key (Go to [Jina AI](https://jina.ai/embeddings/) to get your own API key)

## How to run

**Step1**: Clone the repository

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/auto_embedding/
```

**Step2**: Install the required packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step3**: Set up environment to connect to storage

If you are using TiDB Cloud, you can find the connection parameters in the [TiDB Cloud console](https://tidbcloud.com/) and set up the environment variable like this:

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

If you are using a local TiDB server, you can set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST=localhost
TIDB_PORT=4000
TIDB_USERNAME=root
TIDB_PASSWORD=
TIDB_DATABASE=test
JINA_AI_API_KEY={your-jina-api-key}
EOF
```

**Step4**: Run the demo

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
