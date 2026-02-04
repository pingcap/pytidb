# Vector Index Example

This example demonstrates semantic search with TiDB vector index: a Streamlit app that loads 6000 randomly generated documents on first run, then lets you run vector search and inspect the executed SQL and TiDB execution plan (EXPLAIN ANALYZE).

<p align="center">
  <img width="700" alt="Semantic search with vector embeddings" src="https://github.com/user-attachments/assets/62bbe3d0-e031-4ba3-b1ca-ac0f9d1e628c" />
  <p align="center"><i>Semantic search with vector embeddings</i></p>
</p>

## Prerequisites

- **Python 3.10+**
- **TiDB**: A TiDB Cloud Starter cluster or self-hosted TiDB ([tidbcloud.com](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme))

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

**Step 3**: Configure environment

Copy `.env.example` to `.env` and fill in:

- **TiDB**: Host, port, username, password, database (from [TiDB Cloud console](https://tidbcloud.com/clusters))

```bash
cp .env.example .env
# Edit .env with TIDB_*
```

**Step 4**: Run the Streamlit app

```bash
streamlit run app.py
```

**Step 5**: Open your browser at `http://localhost:8501`

On first load, the app will insert 6000 rows (with a progress bar). Then you can search, filter by language, and view the executed SQL and EXPLAIN ANALYZE result below the results.
