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


## Understanding the project structure

PyTiDB is a single Python package managed through `pyproject.toml`, with optional extras (for docs, models, and the MCP server) pinned in `uv.lock`. The repository is organized as follows:

- `pytidb/`: The core SDK. It houses the SQLModel-based ORM layer, the client/runtime objects, embedding helpers, search logic, and integration points such as rerankers and the MCP server extension.
- `tests/`: High-level integration and regression coverage for every major feature (`tests/test_search_vector.py`, `tests/test_auto_embedding_server.py`, etc.). Tests rely on `pytest` settings declared in `pyproject.toml` and can be run via `make test`.
- `examples/`: Runnable notebooks and scripts grouped by scenario (`examples/vector_search`, `examples/hybrid_search`, `examples/rag`, `examples/image_search`, and more). These mirror the flows described in the README and are useful when verifying feature-level changes.
- `docs/`: MkDocs configuration plus a `quickstart.ipynb`. The public documentation has moved to `pingcap/pingcap.github.io`, but local edits here are still used for experiments and historical references.
- Tooling files (`Makefile`, `.pre-commit-config.yaml`, `.github/`, `.devcontainer/`) define the automation story, and `README.md` provides the product-level overview.

### Core SDK modules (`pytidb/`)

- High-level API surface:
  - `client.py` exposes `TiDBClient`, which wraps SQLAlchemy engines, manages database lifecycle (`create_database`, `use_database`), and issues SQL through `sql.py` helpers.
  - `table.py` builds concrete table handles from SQLModel schemas. It auto-detects vector/text columns, wires up embedding hooks, ensures indexes exist, and exposes CRUD/search helpers.
  - `search.py` implements the fluent search builder for vector, full-text, and hybrid queries. It coordinates embedding lookups, filter translation, reranking, and fusion logic, returning `SearchResult` objects from `result.py`.
- Schema and ORM primitives:
  - `schema.py`, `base.py`, and `datatype.py` provide the SQLModel metaclass, `TableModel` base class, and helpers such as `VectorField` and `FullTextField`. They rely on `pytidb/orm/` (custom TiDB types, index definitions, TiFlash replicas, distance metrics) and `sql.py` for DDL/DML generation.
  - `filters.py` converts the dict-based filter DSL into SQLAlchemy expressions, while `fusion.py` and `rerankers/` handle result scoring (reciprocal-rank fusion, weighted fusion, LiteLLM-based rerankers, etc.).
- AI/ML integrations:
  - `embeddings/` defines `BaseEmbeddingFunction` plus built-in providers, alias mapping, and dimension metadata. Embedding functions attach to `VectorField` definitions and to runtime search requests.
  - `rerankers/` and `fusion.py` plug in optional reranking and hybrid scoring strategies, complementing the primary vector similarity search implemented in `search.py`.
- Infrastructure & extensions:
  - `databases.py`, `utils.py`, and `errors.py` hold lower-level helpers (connection URLs, vector column detection, typed exceptions) used throughout the SDK.
  - `ext/mcp/` exposes the `tidb-mcp-server` entrypoint (registered in `pyproject.toml`) so the client can be driven via the Model Context Protocol.
  - `logger.py` centralizes logging configuration, and `result.py` provides typed containers for raw SQL execution and query outputs.

### How the pieces work together

1. Define your schema by subclassing `schema.TableModel` and using `Field`, `VectorField`, or `FullTextField`. The metadata in those fields drives index creation and auto-embedding.
2. Instantiate a `TiDBClient` via `TiDBClient.connect()`; it constructs the SQLAlchemy engine, optionally ensures the database exists, and is reused across table handles.
3. Build a `Table` from the schema (`client.create_table` or `Table(schema=..., client=client)`), which inspects columns, attaches embedding providers from `embeddings/`, and registers indexes from `orm/indexes.py`.
4. Insert/query data:
   - CRUD paths use SQLModel sessions under the hood (see `table.py` and `result.py`).
   - Search paths call into `search.Search`, which prepares query vectors/text, applies filters (`filters.py`), hits TiDB for vector/full-text scans, optionally reranks, and normalizes responses.
5. Tests under `tests/` and runnable samples under `examples/` exercise each step, and the `Makefile` tasks (`make lint`, `make test`, `make build`) ensure consistent tooling across the repo.

Having this mental model handy makes it easier to locate the right module before opening a PR and keeps new contributions aligned with the existing architecture.
