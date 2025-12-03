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

Understanding how the repository is organized will save you time when you need to find the right abstraction to modify or extend. The top-level layout is intentionally simple:

- `pytidb/`: the installable SDK, exposing the TiDB client, schema helpers, vector/full-text search primitives, embedding wrappers, rerankers, and the MCP integration.
- `tests/`: pytest suites that mirror the public API surface (`test_search_vector.py`, `test_auto_embedding_image.py`, `test_tables.py`, etc.) and ensure every high-level capability remains stable.
- `examples/`: runnable notebooks and scripts grouped by scenario (`basic`, `auto_embedding`, `rag`, `vector_search`, `text2sql`, `image_search`, and more) with shared assets under `examples/assets/`.
- `docs/`: MkDocs-based documentation sources (now mirrored to https://pingcap.github.io/ai) plus a `quickstart.ipynb` that is kept in sync with the examples.
- `pyproject.toml`: project metadata, dependency groups (`mcp`, `pandas`, `models`, and `dev`), and the `tidb-mcp-server` script entry point; `uv.lock`, `.pre-commit-config.yaml`, and the `Makefile` round out the tooling.
- `.github/`, `.devcontainer/`, and `.venv/`: automation, container defaults, and the local virtual environment used by CI and reproducible development shells.

### Core Python package (`pytidb/`)

The SDK centers around a few key layers:

- **Client lifecycle**: `client.py` defines `TiDBClient.connect()` (SQLAlchemy-based engine creation, serverless-aware pooling, database management helpers) and transaction/session utilities. `databases.py` provides creation/existence helpers, while `utils.py` hosts `build_tidb_connection_url`, column inspectors, and TiDB-specific constants. `result.py` wraps SQL execution outputs, and `logger.py` standardizes logging.
- **Schema and table modeling**: `schema.py` builds on SQLModel to define `TableModel`, `VectorField`, `FullTextField`, and distance/index metadata. `table.py` is the high-level Table façade responsible for auto-embedding orchestration, automatic index creation, CRUD helpers, and bulk ingest. Supporting files such as `datatype.py`, `base.py`, and `sql.py` re-export SQLAlchemy types/utilities to contributor code. The `orm/` folder contains TiDB-specific DDL (`orm/sql/ddl.py`), vector data types (`orm/vector.py`), distance metrics, TiFlash replica helpers, and SQLModel extensions.
- **Search, ranking, and fusion**: `search.py` implements the composable query builder that powers vector, full-text, and hybrid queries (filters, rerankers, fusion strategies). `filters.py` turns Mongo-style dictionaries or SQL fragments into SQLAlchemy expressions. `fusion.py` merges heterogeneous search result sets (RRF and weighted strategies) and `rerankers/` provides the LiteLLM-backed reranker implementation.
- **Embeddings and AI adapters**: `embeddings/` contains the abstract base class, builtin/provider-specific implementations, model dimension helpers, and utility functions for handling text/image sources or remote encoding. These modules feed into `table.py`’s auto-embedding pipeline and the search APIs.
- **Integrations**: `ext/mcp/` exposes the `tidb-mcp-server` entry point declared in `pyproject.toml`, wiring the SDK into the Model Context Protocol server so MCP-compatible clients can provision, query, or administer TiDB instances.

Collectively, the architecture flows from `TiDBClient` → `Table`/`TableModel` → `Search`/`Fusion` → `Result`, with embeddings and rerankers acting as optional accelerators. When adding new features, prefer extending the existing layer that already encapsulates the concern—for example, update `filters.py` if you need a new predicate operator or add a helper under `embeddings/` if a provider-specific quirk must be handled.

### Tests, docs, and examples

- The `tests/` directory mirrors user workflows: schema creation (`test_tables.py`), SQLModel bindings (`test_sql_model.py`), raw SQL execution, vector/full-text/hybrid search, fusion, transaction handling, and auto-embedding across text and image modalities. Extending functionality usually means adding or updating a dedicated test module here.
- `examples/` double as integration tests and documentation—each subfolder shows end-to-end flows (e.g., `vector-search-with-realtime-data` demonstrates ingest + hybrid retrieval, `memory/` covers session state, and `rag/` stitches embeddings with rerankers). If you ship a feature that benefits from a tutorial, place it alongside the closest existing scenario.
- `docs/` currently hosts a MkDocs site consumed by the central documentation repo; keep its `src/` guides and `quickstart.ipynb` synchronized with API changes to avoid drift for downstream readers.

Use this overview as your map: confirm where a change belongs, adjust accompanying tests/examples/docs in the same area, and keep `pyproject.toml` (dependency groups and entry points) in sync when you introduce new optional features.
