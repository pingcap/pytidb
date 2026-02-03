# Vector Index Example

This example demonstrates semantic search with TiDB vector index: a Streamlit app that loads 1000 randomly generated documents on first run, then lets you run vector search and inspect the executed SQL and TiDB execution plan (EXPLAIN ANALYZE).

<p align="center">
  <img width="700" alt="Semantic search with vector embeddings" src="https://github.com/user-attachments/assets/6d7783a5-ce9c-4dcc-8b95-49d5f0ca735a" />
  <p align="center"><i>Semantic search with vector embeddings</i></p>
</p>

## Prerequisites

- **Python 3.10+**
- **A TiDB Cloud Starter cluster**: Create a free cluster here: [tidbcloud.com ↗️](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme)

## How to run

**Step 1**: Clone the repository and go to the example

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/vector_index/
```

**Step 2**: Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r reqs.txt
```

**Step 3**: Set up environment to connect to TiDB

Go to [TiDB Cloud console](https://tidbcloud.com/clusters) and get the connection parameters, then set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST={gateway-region}.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USERNAME={prefix}.root
TIDB_PASSWORD={password}
TIDB_DATABASE=vector_index_example
EOF
```

**Step 4**: Run the Streamlit app

```bash
streamlit run app.py
```

**Step 5**: Open your browser at `http://localhost:8501`

On first load, the app will insert 1000 rows (with a progress bar). Then you can search, filter by language, and view the executed SQL and EXPLAIN ANALYZE result below the results.
