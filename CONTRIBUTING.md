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

Understanding where each capability lives makes it easier to decide where to add features or tests:

- `pytidb/`: Core SDK package that is published to PyPI. `client.py` exposes `TiDBClient` for connection management, `table.py` wraps SQLModel tables and query helpers, and `schema.py` / `orm/` hold SQLModel models, index helpers, and TiFlash replica utilities. Search features are implemented in `search.py`, `filters.py`, `fusion.py`, and `result.py`. Vector-adjacent functionality is split into `embeddings/` (providers, dimensions, helpers) and `rerankers/` (LiteLLM-based rerankers). `ext/mcp/` powers the `tidb-mcp-server` entry point, while `utils.py`, `databases.py`, `logger.py`, and `sql.py` provide shared plumbing.
- `tests/`: Pytest suite that mirrors the public API surface (connection management, search modes, transactions, ORM helpers, utilities). Use it as a reference for expected behavior when modifying modules under `pytidb/`.
- `examples/`: Ready-to-run notebooks and scripts grouped by scenario (`vector_search/`, `rag/`, `text2sql/`, `auto_embedding/`, etc.). These double as smoke tests for larger workflows.
- `docs/`: MkDocs site definition. `docs/mkdocs.yml` configures the Material theme, redirects, and extra styles in `docs/src/styles`. Use `uv run mkdocs build` (from the `docs/` directory) to preview documentation changes.
- `pyproject.toml`: Source of truth for build metadata, runtime dependencies, optional extras (e.g., `models`, `mcp`), and uv workspace settings. `uv.lock` pins exact versions for reproducible installs across the SDK and docs site.
- `Makefile`: Shortcuts for common workflows (`install`, `lint`, `format`, `test`, `build`, `publish`) and they default to running under uv so contributors share the same tooling.
