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

## Project structure

Understanding how the SDK is laid out makes it easier to find the right extension points when you fix bugs or add features.

### Directory layout

- `pytidb/` — the library itself. It is a typed SQLModel/SQLAlchemy layer with vector, full-text, and hybrid search utilities plus integrations such as embeddings, rerankers, and the MCP server entry point.
- `tests/` — pytest suites (for example `tests/test_search_vector.py`, `tests/test_tables.py`, `tests/test_transaction.py`) and shared helpers in `tests/utils.py` and `tests/fixtures/`. They cover search, schema/index management, transactions, utilities, and regression tests for embedding pipelines.
- `docs/` — the MkDocs site (`docs/mkdocs.yml`, `docs/src/index.md`, `docs/src/assets/`, `docs/src/styles/`) and a Quickstart notebook (`docs/quickstart.ipynb`). This folder is also listed as an `uv` workspace member for docs-specific dependencies.
- `examples/` — runnable notebooks and scripts grouped by use case (`examples/vector_search`, `examples/hybrid_search`, `examples/auto_embedding`, `examples/text2sql`, `examples/vector-search-with-realtime-data`, etc.). They mirror the scenarios covered by the tests and are the best reference for end-to-end flows.

### Core modules inside `pytidb/`

- `client.py` — defines `TiDBClient`, which wraps SQLAlchemy engines, manages connection/session context (`SESSION`), database lifecycle helpers (`create_database`, `use_database`, `session()`), and high-level helpers such as `create_table`, `query`, and `execute`.
- `table.py` — the `Table` façade around SQLModel `TableModel` schemas. It inspects vector/text columns, wires default search columns, sets up auto-embedding, and automatically builds `VectorIndex`/`FullTextIndex` objects. It also exposes CRUD helpers that reuse builders from `pytidb.sql`.
- `schema.py` — home to `TableModel`, `VectorField`, `FullTextField`, index helpers, and type aliases such as `DistanceMetric`, `VectorDataType`, and `QueryBundle`. It is where new models declare TiDB-specific metadata (auto embedding, TiFlash replicas, custom parsers).
- `databases.py`, `datatype.py`, `base.py`, and `utils.py` — low-level utilities for spinning up databases, exposing TiDB data types (including `VECTOR`), generating SQLAlchemy declarative bases, building TiDB connection URLs, and validating vector/text column metadata.
- `sql.py`, `filters.py`, and `fusion.py` — query-building primitives. `sql.py` re-exports the SQLModel/SQLAlchemy DSL in one namespace, `filters.py` turns structured JSON/dict filters into SQLAlchemy expressions, and `fusion.py` merges vector and full-text result sets via RRF or weighted scoring.
- `search.py` — the fluent search builder that powers vector, full-text, and hybrid search. It handles query parsing, pre/post filters, rerankers, scoring labels, and result materialization into `SearchResult` models.
- `result.py`, `errors.py`, and `logger.py` — shared result containers (`SQLQueryResult`, `SQLExecuteResult`), SDK-level exceptions, and logging setup so client and table helpers emit consistent diagnostics.
- `embeddings/` — base classes plus built-in providers, dimension utilities, and auto-embedding glue. The directory contains `BaseEmbeddingFunction`, provider aliases, and helpers for server-side embedding via TiDB functions.
- `rerankers/` — reranker abstractions (`BaseReranker`) and concrete adapters such as `LiteLLMReranker` for litellm-powered re-ranking of candidate documents.
- `orm/` — TiDB-specific SQLModel/SQLAlchemy extensions: custom column/index types (`vector.py`, `types.py`), DDL generation (`orm/sql/ddl.py`), index definitions (`VectorIndex`, `FullTextIndex`), TiFlash replica helpers, and information_schema utilities.
- `ext/mcp/` — the Model Context Protocol server (`tidb-mcp-server` entry point defined in `pyproject.toml`). It uses `TiDBClient` under the hood to expose `db_query`, `switch_database`, and other MCP tools.

### How the pieces fit together

1. You declare tables by subclassing `pytidb.schema.TableModel` (optionally using `VectorField`/`FullTextField`). The schema metadata is consumed by `pytidb.table.Table`.
2. `TiDBClient.connect()` (in `client.py`) creates the SQLAlchemy engine, ensures databases exist via `pytidb.databases`, and exposes transactional helpers. Calling `client.create_table(schema=MyModel)` hands the schema to `Table` so it can emit DDL with TiDB vector/full-text indexes.
3. Reads funnel through `Table.search()` (wrapping `pytidb.search.Search`), which builds SQL via `pytidb.sql`, applies structured filters (`filters.py`), optionally calls embeddings (`pytidb.embeddings`) and rerankers (`pytidb.rerankers`), then merges results (`fusion.py`). Outputs are normalized through the classes in `result.py`.
4. Both docs and examples import the same APIs. Integration tests in `tests/` assert the behavior end-to-end (index creation, hybrid search, TiFlash replicas, transactions, and utilities like `filters`), so referencing the matching test file is the fastest way to understand expectations before editing a module.
