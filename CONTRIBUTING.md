# How to contribute

Thank you for your interest in contributing to the TiDB Python SDK project!

## Understand the project structure (start here)

### Where do I start?
- Skim `README.md` and `examples/quickstart` to see TiDBClient/Table usage end-to-end before diving into internals.
- Run one of the self-contained samples in `examples/basic` or `examples/vector_search`—each mirrors a feature-focused slice of the library and is the fastest way to reproduce issues.
- Open `tests/test_tables.py`, `tests/test_search_*.py`, or `tests/test_auto_embedding_*.py` that match the feature you plan to touch; these tests double as living documentation of expected behavior.

### How the pieces fit together
1. `pytidb/client.py` exposes `TiDBClient.connect()` which builds a SQLAlchemy engine (`pytidb/utils.py`) and wraps database management helpers (`pytidb/databases.py`).
2. Schemas are declared with `pytidb/schema.py` (`TableModel`, `VectorField`, `FullTextField`) and compiled into SQLModel tables via `pytidb/base.py`.
3. `pytidb/table.py` couples a schema to a connected client, auto-creates indexes, configures embeddings, and surfaces CRUD/search entry points.
4. Query-time features live in `pytidb/search.py` (vector/full-text/hybrid pipelines), `pytidb/filters.py` (JSON-like filter DSL), `pytidb/fusion.py` (RRF / weighted fusion), and `pytidb/rerankers` (LiteLLM-backed reranking strategies).
5. Lower-level TiDB specifics—custom datatypes, indexes, TiFlash replicas, and SQL helpers—sit in `pytidb/orm/*` and are reused by higher layers.
6. Results are unified in `pytidb/result.py`, while surrounding utilities (`pytidb/logger.py`, `pytidb/errors.py`, `pytidb/datatype.py`) keep the surface ergonomic.

This flow mirrors runtime execution: `TiDBClient` → `Table` → `Search/SQL helpers` → `Result`, with embeddings/rerankers optionally plugged in along the way.

### Directory and module navigation guide
- `pytidb/`: Top-level SDK code. Start with `client.py`, `table.py`, `search.py`, and `schema.py`; branch into `embeddings/`, `rerankers/`, `filters.py`, `fusion.py`, or `utils.py` depending on the feature.
- `pytidb/orm/`: Dialect extensions (vector types, TiFlash replica config, custom indexes, SQL DDL builders). Touch these when TiDB-specific behavior or SQL code generation needs changes.
- `pytidb/ext/mcp/`: The MCP server shim that wraps the SDK—useful when fixing CLI/server integrations.
- `examples/`: Scenario-based samples. Each directory (e.g., `vector_search`, `fulltext_search`, `rag`) maps directly to similarly named tests and modules—keep them in sync when adding features.
- `tests/`: Pytest suites organized by behavior (`test_search_vector.py`, `test_index_fulltext.py`, `test_transaction.py`, etc.). Every change should either extend an existing test module or add a new file that mirrors the module you touched.
- `docs/`: MkDocs site sources plus notebooks (`docs/src` and `docs/quickstart.ipynb`). Follow the same structure when documenting new APIs.
- Tooling roots: `pyproject.toml` + `uv.lock` define dependencies, `Makefile` exposes `format`, `lint`, `test`, and docs preview targets.

### Common contribution journeys
1. **Fix a query/search bug**
   - Start in `pytidb/search.py` and `pytidb/filters.py` to understand how queries are assembled.
   - Reproduce with `examples/vector_search` or `tests/test_search_vector.py`, then add/adjust tests under `tests/test_search_*.py`.
   - Validate that results still serialize correctly by touching `pytidb/result.py` only if shapes change.
2. **Add or adjust schema/DDL behavior**
   - Modify `pytidb/schema.py`, supporting datatypes in `pytidb/datatype.py`, or TiDB-specific extensions inside `pytidb/orm`.
   - Exercise changes through `tests/test_tables.py`, `tests/test_sql_model.py`, and the migration-heavy samples in `examples/basic`.
3. **Introduce a new embedding or reranker**
   - Implement providers in `pytidb/embeddings/` or `pytidb/rerankers/`, then wire them into `pytidb/table.py` auto-embedding hooks.
   - Document usage under `examples/auto_embedding` or `examples/image_search` and cover behavior with the corresponding `tests/test_auto_embedding_*.py`.
4. **Doc or tooling improvements**
   - Update prose in `docs/src`, Jupyter notebooks in `docs/quickstart.ipynb`, or developer ergonomics in `Makefile`/`pyproject.toml`.
   - Use `examples/` for runnable snippets referenced in docs to keep drift low.

### Development workflow within this structure
- Keep feedback loops tight: reproduce the issue with an example, lock in expectations via a targeted test, then edit the module in `pytidb/`.
- Favor the smallest surface area: many files re-export helpers (e.g., `pytidb/sql.py`, `pytidb/utils.py`), so update the root module rather than duplicating logic downstream.
- Run scoped tests (`uv run pytest tests/test_search_vector.py -k "<case>"`) before full suites to stay productive, then finish with `uv run pytest` or `make test`.
- Mirror any code change in user-facing material—examples, docs, or release notes—so contributors after you know where to start.

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
