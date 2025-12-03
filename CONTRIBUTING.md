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

## Project Structure Overview

Understanding how the repository is organized makes it easier to decide where new features, bug fixes, or docs should live.

### Top-level layout

| Path | Purpose |
| --- | --- |
| `pytidb/` | Core SDK package (client APIs, schema & table runtime, search pipeline, embedding/reranker integrations, utilities). |
| `docs/` | MkDocs-powered documentation site (`docs/mkdocs.yml`, its own `pyproject.toml`, and Markdown/asset sources under `docs/src/`). |
| `examples/` | Runnable samples for the major scenarios (`vector_search`, `fulltext_search`, `hybrid_search`, `image_search`, `rag`, `text2sql`, etc.). |
| `tests/` | Pytest suite that covers auto-embedding (text/image/server), filters, hybrid/vector/full-text search, TiFlash replicas, transactions, and helper utilities. |
| `.github/` | Issue templates plus CI workflows that run formatting (`ruff`), tests, and publishing jobs. |
| `.devcontainer/`, `.vscode/` | Editor/Dev Container defaults that mirror the documented local setup. |
| `pyproject.toml` | Declares project metadata, optional extras (`pandas`, `models`, `mcp`), dev dependencies, and exposes the `tidb-mcp-server` console script. |
| `Makefile`, `uv.lock` | Common contributor commands (`install`, `lint`, `test`, `build`, `publish`) and the lockfile that keeps `uv` environments reproducible. |

### Core library modules (`pytidb/`)

- `client.py`, `databases.py`, `utils.py`: `TiDBClient` connection manager, database helpers (create/list/ensure), connection URL builders, and TiDB Serverless-aware pooling/SSL defaults.
- `schema.py`: SQLModel-based `TableModel`, `VectorField`, and `FullTextField` helpers, distance metrics, and index metadata used throughout the ORM layer.
- `table.py`: Runtime wrapper around a schema that configures automatic embeddings, creates vector/full-text indexes, exposes CRUD helpers, and bridges to the search APIs.
- `search.py`, `filters.py`, `fusion.py`: Query builder for vector/full-text/hybrid search, filter DSL (`$and`, `$or`, `$in`, …), reranker hooks, and result-fusion strategies (reciprocal-rank and weighted scoring).
- `embeddings/`: Base + built-in embedding functions (LiteLLM-backed providers, text/image processing, caching, dimension inference) used by auto-embedding and manual workflows.
- `rerankers/`: Pluggable reranker abstractions plus the LiteLLM implementation that hybrid search relies on.
- `sql.py`, `result.py`, `errors.py`, `logger.py`: Thin SQLAlchemy re-exports, `QueryResult` helpers (`SQLQueryResult`, `SQLModelQueryResult`), exception helpers, and logging defaults.
- `orm/`: TiDB-specific SQLModel/SQLAlchemy extensions (vector column types, index DDL, TiFlash replica helpers, distance metrics, MCP variables).
- `ext/mcp/`: The Modular Command Platform server (`tidb-mcp-server`) that exposes TiDB operations over MCP-compatible tooling.

> `embeddings/`, `rerankers/`, and several hybrid-search features depend on the optional `pytidb[models]` extra (LiteLLM, Pillow, etc.).

### Architecture at a glance

1. **Connect**: `TiDBClient.connect()` (plus helpers such as `create_database`, `use_database`, and the session context manager) creates SQLAlchemy engines with TiDB-aware defaults (Serverless pooling, SSL, retries).
2. **Model**: Define tables by subclassing `pytidb.schema.TableModel` with `VectorField` / `FullTextField`. Those metadata drive auto-indexing and embedding behavior when the table is materialized.
3. **Operate on tables**: `Table(client=…, schema=…)` bootstraps automatic embeddings, manages default text/vector columns, and exposes CRUD helpers (`bulk_insert`, `update`, `delete`, `query`, etc.).
4. **Search & retrieval**: `Table.search()` yields a `Search` builder that orchestrates embedding generation, filter application, rerankers, and fusion strategies before returning `SearchResult` / `QueryResult` objects.
5. **Extended surface area**: The `embeddings` & `rerankers` packages plug in new providers, `ext/mcp` exposes those capabilities via MCP, `examples/` and `docs/` keep user-facing guides in sync, and `tests/` verify every layer (indexes, filters, TiFlash replicas, transactions, hybrid/vector/full-text search).

Use this map to identify the right place for code changes, documentation updates, and regression tests before opening a PR.
