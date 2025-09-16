# GraphRAG Demo

This example demonstrates how to use PyTiDB to build a GraphRAG application.

* Use PyTiDB Client to connect to TiDB
* Create a table with text, vector, and JSON columns
* Perform GraphRAG operations on data

## Prerequisites

- **Python 3.10+**
- **A TiDB Cloud Starter cluster**: Create a free cluster here: [tidbcloud.com ↗️](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme)

## How to run

**Step 1**: Clone the repository to local

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/graphrag/
```

**Step 2**: Install the required packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step 3**: Set up environment to connect to database

Go to [TiDB Cloud console](https://tidbcloud.com/clusters) and get the connection parameters, then set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST={gateway-region}.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USERNAME={prefix}.root
TIDB_PASSWORD={password}
TIDB_DATABASE=graphrag_example
EOF
```

**Step 4**: Run the demo

```bash
streamlit run app.py
```
