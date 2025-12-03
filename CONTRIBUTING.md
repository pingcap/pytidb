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

## Understand the project structure

Having a mental map of the repository makes it much easier to decide where a change should live.

### Top-level layout

| Path | Description |
| --- | --- |
| `pytidb/` | Source for the TiDB Python AI SDK. Most contributions land here. |
| `tests/` | pytest suite that exercises connection management, schema helpers, filters, search modes, embedding flows, and ORM utilities. |
| `examples/` | End-to-end samples (basic CRUD, RAG, hybrid search, custom embeddings, Text2SQL, routing real-time data, etc.) that you can run against a TiDB cluster. |
| `docs/` | MkDocs site that now mirrors <https://pingcap.github.io/ai>. Contains `mkdocs.yml`, a standalone `pyproject.toml`, and `src/` with landing pages/styles. |
| `Makefile` | Convenience targets for installing dependencies with `uv`, running `ruff`, tests, builds, and publishing. |
| `pyproject.toml` / `uv.lock` | Shared dependency, tooling, and build configuration for the root package. |

### Core SDK modules inside `pytidb/`

- `client.py`: exposes `TiDBClient`, a SQLAlchemy-powered engine wrapper that knows how to connect, ensure databases, swap schemas (`use_database`), and list/manage tables. It is the entry point new apps instantiate.
- `schema.py`: builds on SQLModel to define `TableModel`, `VectorField`, `FullTextField`, distance metrics, and helper metadata the rest of the stack consumes. This is how contributors declare tables, indexes, and embedding behavior.
- `table.py`: wraps a `TableModel` plus `TiDBClient` to provide CRUD, automatic vector/full-text index creation, and auto-embedding plumbing. It inspects `__pydantic_fields__` to discover vector/text fields, attaches indexes, and exposes fluent APIs (`insert`, `bulk_insert`, `search`, etc.).
- `search.py`: implements vector, full-text, and hybrid search builders. It handles query embedding, thresholding, reranking hooks, result fusion, and exports typed `SearchResult` objects.
- `filters.py`: transforms dict-like filters or SQLAlchemy expressions into executable clauses shared by both search and table APIs.
- `embeddings/`: abstract base plus built-in providers (OpenAI, Jina, etc.), dimension metadata, and utilities for converting sources or queries. `VectorField` hooks into whichever `EmbeddingFunction` you configure so server-side and client-side embeddings stay transparent.
- `rerankers/`: base class plus a LiteLLM-powered implementation for optional reranking during search.
- `fusion.py` & `result.py`: helper utilities for combining search outputs (RRF/weighted) and normalizing SQL query results to `QueryResult`, `SQLModelQueryResult`, or simple dict/list conversions.
- `orm/`: TiDB-specific SQLAlchemy/SQLModel extensions such as the `VECTOR` data type, vector/full-text indexes, TiFlash replica descriptors, expression helpers, and distance metric validation.
- `ext/mcp/`: implementation of the `tidb-mcp-server` entry point declared in `pyproject.toml`. It bootstraps a Model Context Protocol server that exposes TiDB operations to AI agents.
- `utils.py` / `databases.py` / `logger.py` / `errors.py`: shared plumbing for connection URLs, TiDB-specific validations, logging, and error translation.

### Supporting project areas

- `examples/*`: Organized by scenario (`basic`, `rag`, `fulltext_search`, `memory`, `vector-search-with-realtime-data`, etc.). Each folder contains runnable scripts or notebooks that demonstrate how higher-level abstractions should be used. When you add new functionality, consider dropping a runnable sample here.
- `tests/*`: Mirrors the main modules—`test_databases.py`, `test_tables.py`, `test_search_vector.py`, `test_auto_embedding_*`, `test_filters.py`, and so on. When you touch a feature, look for the matching test file to extend. Fixtures in `tests/fixtures/` and helpers in `tests/utils.py` keep database setup predictable.
- `docs/`: Although the public docs now live in `pingcap/pingcap.github.io`, this directory still holds the MkDocs site (with `docs/src/index.md`, shared assets, and `quickstart.ipynb`). Use it when you need to preview documentation locally or author notebooks before upstreaming them.

### How the pieces fit together

1. **Client & database management** – `TiDBClient.connect()` creates SQLAlchemy engines, optionally ensuring the target database, and exposes helpers (`create_database`, `list_tables`, `session()` context managers) that other layers share.
2. **Schema definition** – Contributors describe their tables by subclassing `TableModel` and using `Field`, `VectorField`, or `FullTextField`. Vector fields can attach embedding functions (client-side or server-side via `func.EMBED_TEXT`) and index metadata.
3. **Table orchestration** – `Table` binds a schema to a client, inspects declared vector/text fields, configures auto-embedding (tracking source columns, provider metadata, and server/client execution), and ensures supporting indexes exist before data flows in.
4. **Search execution** – `Table.search()` instantiates `Search`, which can run vector, full-text, or hybrid pipelines. It pulls embeddings via `embeddings/`, applies filter clauses, pre/post-filters candidates, optionally reranks with `rerankers/`, and fuses heterogeneous result sets with `fusion.py`.
5. **Results & integrations** – Executed statements return `QueryResult`/`SQLQueryResult` wrappers that can be converted to dicts, lists, pandas DataFrames, or SQLModel instances. External clients (examples, MCP server, notebooks) rely on these conversions for downstream tasks.

Keep this workflow in mind when updating docs or code—changes to schemas typically cascade into table constructors, search behavior, tests, and user-facing samples.
