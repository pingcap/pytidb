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

## Project structure overview

Understanding how PyTiDB is laid out will make it easier to decide where a change should live.

### Top-level layout
- `pytidb/` – the Python package that ships to PyPI. This is where the TiDB client, ORM utilities, search pipeline, embedding helpers, and integration points live.
- `tests/` – pytest-based coverage for the public API (client/database management, vector + full-text search modes, auto-embedding, indexes, transactions, utilities, etc.).
- `examples/` – runnable notebooks and scripts that demonstrate features such as auto-embedding, hybrid search, RAG, and text-to-SQL.
- `docs/` – the MkDocs site configuration. The rendered content has moved to [`pingcap/pingcap.github.io`](https://github.com/pingcap/pingcap.github.io), but this directory still contains the source notebooks and shared config referenced by the README.
- `Makefile`, `pyproject.toml`, `uv.lock` – shared tooling for installing dependencies, running lint/tests, and building/publishing packages.

### Core Python package highlights (`pytidb/`)
- `client.py` exposes `TiDBClient`, a thin layer over SQLAlchemy engines with helpers for provisioning databases, switching schemas, and wiring connection/session state that downstream components consume.
- `schema.py` defines the `TableModel` base class plus helpers such as `VectorField` and `FullTextField` that embed schema metadata (dimensions, embedding functions, index hints) into SQLModel definitions.
- `table.py` wraps a `TableModel` and adds lifecycle management: creating tables, syncing auto-embedding configs, enforcing index conventions, and dispatching CRUD/search operations against the active `TiDBClient`.
- `search.py`, `filters.py`, and `fusion.py` implement the high-level query pipeline. They translate vector/text queries into SQL, attach filters, call optional rerankers, and fuse multi-operator searches (vector + full-text + weighted/rrf fusion).
- `embeddings/` and `rerankers/` provide pluggable interfaces plus builtin providers for automatic embedding and re-ranking. These modules are shared by the auto-embedding hooks in `table.py` as well as the Model Context Protocol server.
- `orm/` contains TiDB-specific SQLModel/SQLAlchemy primitives such as index types, TiFlash replica helpers, distance metrics, and TiDB SQL functions. These are re-exported by `schema.py` so contributors rarely touch raw SQL.
- `ext/mcp/` implements the `tidb-mcp-server` entrypoint defined in `pyproject.toml`, allowing PyTiDB to act as an MCP server for IDE agents.
- Supporting modules (`databases.py`, `sql.py`, `result.py`, `errors.py`, `logger.py`, `utils.py`) encapsulate connection utilities, SQL builders, structured result containers, and shared logging/error handling.

### Supporting assets for contributors
- `examples/` and `docs/src/` are great references for end-to-end flows—mirror their patterns when documenting or testing new capabilities.
- `tests/` double as usage documentation; add or update tests beside the functionality you touch to preserve coverage for the different search modes and schema helpers.
