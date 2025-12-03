# How to contribute

Thank you for your interest in contributing to the TiDB Python SDK project!

## Setup the development environment

To set up the development environment with pytidb, follow these steps:

```bash
# Clone github repo
git clone https://github.com/pingcap/pytidb.git

# Change directory into project directory
cd pytidb

# Install uv if you don't have it already
pip install uv

# Install pytidb with all dependencies
uv sync --dev
```

## Project Structure

A quick tour of the repository helps new contributors find the right entry points:

### Top-level directories

- `pytidb/`: the Python package that ships to PyPI. Files like `client.py`, `table.py`, `databases.py`, and `search.py` implement the core SDK primitives for connecting to TiDB, managing tables, and running vector/full-text/hybrid searches.
- `pytidb/embeddings` and `pytidb/rerankers`: pluggable embedding functions and rerankers (LiteLLM-powered by default) that back features such as auto-embedding, multi-modal search, and result fusion.
- `pytidb/orm`: strongly-typed schema utilities (`TableModel`, field definitions, index helpers, TiFlash replica helpers) that mirror TiDB's SQL/DDL capabilities.
- `pytidb/ext/mcp`: the `tidb-mcp-server` CLI entry point (`pytidb.ext.mcp:main`) that exposes the SDK to Model Context Protocol clients.
- `tests/`: pytest suites covering search modes, embedding flows, SQL utilities, and transactional behavior. Use `make test` or `uv run pytest` before submitting a PR.
- `examples/`: runnable walkthroughs (vector/full-text/hybrid search, RAG, text2sql, image search, etc.) showing end-to-end SDK usage.
- `docs/`: MkDocs-based documentation (`docs/mkdocs.yml`, `docs/src/index.md`, and assets). Run `mkdocs build` or `mkdocs serve` from this folder to preview changes.

### Supporting files

- `README.md`: high-level product overview, installation guidance, and quick-start snippets.
- `pyproject.toml`: project metadata, core dependencies (SQLModel, SQLAlchemy, PyMySQL, NumPy), optional extras (models, pandas, MCP), and dev-tooling definitions.
- `uv.lock`: the resolved dependency graph used by `uv sync`.
- `Makefile`: convenience targets for installing, linting (`ruff`), testing, building, and publishing packages.
