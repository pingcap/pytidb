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

## Project structure & architecture

Understanding how the repository is laid out will help you quickly find the right place for a change and wire it up consistently.

### Directory layout

- `pytidb/` - the runtime package that is published to PyPI. This folder houses the TiDB client, schema definition helpers, search pipeline, AI integrations, and utilities that power the SDK.
- `tests/` - pytest suites that exercise every feature (auto-embedding, filters, search modes, TiFlash replicas, transactions, etc.). Add or extend tests next to the feature you touch (for example, `tests/test_search_vector.py` for vector search changes).
- `examples/` - runnable notebooks/scripts grouped by scenario (`auto_embedding/`, `hybrid_search/`, `image_search/`, `text2sql/`, `vector-search-with-realtime-data/`, ...). They double as smoke tests when you need to validate an end-to-end flow.
- `docs/` - MkDocs-based site (`docs/mkdocs.yml`, `docs/src/...`) plus the `docs/pyproject.toml` workspace. Use this when updating the public documentation or building previews.
- Tooling files live at the repo root: `pyproject.toml` defines the published package and dependency groups, `uv.lock` locks versions, `Makefile` provides common workflows (`make test`, `make lint`, etc.), and `README.md` gives the user-facing overview.

### Key runtime modules

- `pytidb/client.py` defines `TiDBClient`, which owns SQLAlchemy engine creation, database management helpers (`create_database`, `use_database`, etc.), and higher-level CRUD/search entry points. It is the main surface new integrations plug into.
- `pytidb/schema.py` introduces the `TableModel` base (built on SQLModel) plus helpers such as `VectorField` and `FullTextField` for declaring embeddings, text columns, indexes, and TiFlash replicas in a declarative way.
- `pytidb/table.py` wraps a `TableModel` into a runtime `Table` object. It wires auto-embedding, manages default vector/text columns, provisions vector/full-text indexes, and exposes methods like `bulk_insert`, `search`, and `update`.
- `pytidb/search.py` implements the fluent search builder that powers vector, full-text, and hybrid search. It coordinates filters, scoring, reranking, and fusion strategies, returning `SearchResult` objects or Pandas/SQLModel data.
- `pytidb/filters.py` converts dictionary-style or SQLAlchemy filter expressions into reusable clauses, so `Search` and raw queries can share the same filter syntax.
- `pytidb/fusion.py` merges vector and full-text hits using Reciprocal Rank Fusion or weighted blending, keeping track of `_score`, `_distance`, and `_match_score`.
- `pytidb/embeddings/` contains the `BaseEmbeddingFunction` abstractions, built-in providers (`EmbeddingFunction`), dimension helpers, and shared utilities for auto-generating embeddings either client-side or via TiDB Serverless functions.
- `pytidb/rerankers/` provides the reranker interfaces plus the LiteLLM-backed implementation used by hybrid search to refine ordered results.
- `pytidb/orm/` is the TiDB-specific SQLModel layer: custom column types (including `VECTOR`), index definitions (`VectorIndex`, `FullTextIndex`), distance metrics, TiFlash replica helpers, and SQL snippets used across the package.
- Supporting modules such as `pytidb/databases.py`, `pytidb/result.py`, `pytidb/utils.py`, `pytidb/datatype.py`, and `pytidb/errors.py` host database helpers, result adapters, connection/url utilities, type exports, and shared exceptions. The optional `pytidb/ext/mcp/` folder backs the `tidb-mcp-server` CLI entry point.

### How the pieces fit together

1. **Schema definition** - Contributors declare tables by subclassing `TableModel` (`pytidb/schema.py`) and composing fields from `pytidb/datatype.py` plus `VectorField`/`FullTextField`. Schema metadata (index hints, embedding sources, TiFlash replicas) is stored alongside the model.
2. **Client and table lifecycle** - `TiDBClient.connect()` (`pytidb/client.py`) builds a SQLAlchemy engine, optionally ensures the database exists, and surfaces helpers (`create_table`, `drop_table`, `execute_sql`, ...). When a table is created, `pytidb/table.py` inspects the schema, establishes default vector/text columns, and automatically wires embedding/index behavior.
3. **Query & search pipeline** - `Table.search()` instantiates the `Search` builder (`pytidb/search.py`). It can accept raw vectors, text, or image paths, apply structured filters from `pytidb/filters.py`, blend vector/full-text scores via `pytidb/fusion.py`, and optionally apply rerankers from `pytidb/rerankers/`.
4. **AI features** - When a `VectorField` references an embedding function, `Table` automatically triggers the configured `pytidb/embeddings` provider to populate the vector column during `insert`/`bulk_insert`. Hybrid search can further feed results into rerankers for better ordering.
5. **Result handling** - Query outcomes are wrapped by `pytidb/result.py` so callers can switch between raw rows, Pydantic models, or Pandas DataFrames without re-writing queries.

Use this mental model when making changes: start with the `pytidb/` module that owns the behavior, cover it with the corresponding test in `tests/`, document end-to-end usage in `examples/` or `docs/` if the surface area changes, and wire any new CLI or automation through the existing Makefile/uv workflows.
