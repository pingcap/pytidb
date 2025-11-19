# How to contribute

Thank you for your interest in contributing to the TiDB Python SDK project!

## Project Core Structure

```text
pytidb/
├── pytidb/                 # Runtime SDK package shipped to PyPI
├── tests/                  # Pytest suites plus fixtures/utilities
├── docs/                   # MkDocs site + notebooks (separate uv member)
├── examples/               # Scenario-driven integration examples
├── pyproject.toml          # Build metadata, extras, scripts
├── uv.lock                 # Locked dependency graph shared via uv
├── Makefile                # Common install/lint/test/build shortcuts
├── .github/workflows/      # CI for linting, testing, publishing
└── .devcontainer/.vscode   # Editor + Codespace defaults
```

### `pytidb/` – runtime SDK layer

- **Purpose**: Houses the SDK that wraps TiDB SQL + AI capabilities. Everything under this package is packaged into the published wheel via `pyproject.toml` and Hatch.
- **Key modules**:
  - `client.py` (`TiDBClient`) manages SQLAlchemy engines, database lifecycle helpers (`databases.py`), and provides session-scoped APIs backed by `contextvars` for safe reuse.
  - `schema.py`, `table.py`, `result.py`, and `search.py` define the declarative object model (`TableModel` → `Table`) and fluent query/search pipeline that combine SQLModel metadata, automatic embedding hooks, and serialization helpers.
  - `filters.py`, `fusion.py`, `sql.py`, `datatype.py`, `utils.py`, and `logger.py` provide infrastructural helpers used by the surface APIs. They keep SQL parsing, type conversion, and logging concerns separated.
- **Technical relationships**: Contributors typically design new features by extending `TableModel` (SQLModel declarative base defined in `base.py`) and implementing orchestration in `Table`. `TiDBClient` instantiates `Table` objects and forwards requests to SQLAlchemy. Result sets move through `result.SQL*` containers before being converted to Pydantic, pandas, or lists.
- **Design patterns**: Declarative models (SQLModel) capture schema intent; repository-like `Table` objects centralize CRUD/search logic; context-managed sessions enforce unit-of-work semantics.

#### Embedding subsystem (`pytidb/embeddings/`)

- Maintains provider-agnostic APIs (`base.py`) plus registry/alias utilities (`aliases.py`, `dimensions.py`, `utils.py`).
- Built-in providers live in `builtin.py` and depend on optional extras declared under `[project.optional-dependencies]` (`models`, `pandas`).
- Embedding strategies hook into `Table.search()` by emitting vector field definitions via `EmbeddingFunction.VectorField`, letting contributors add new providers by implementing the same base protocol.

#### Reranking subsystem (`pytidb/rerankers/`)

- Defines a strategy interface in `base.py` and concrete Litellm-powered implementations in `litellm.py` for post-processing ranked lists.
- Works alongside embeddings in `search.py` by chaining rerankers onto hybrid search. New rerankers should follow the same plug-in model and declare optional dependencies in `pyproject.toml`.

#### ORM + TiDB extensions (`pytidb/orm/`, `pytidb/ext/`)

- `pytidb/orm/` encapsulates TiDB-specific SQLModel helpers: index definitions, distance metrics, system tables (`information_schema.py`), TiFlash replica helpers, and SQL templates (`sql/`). These files keep DDL concerns reusable across the SDK.
- `pytidb/ext/mcp/` exposes the `tidb-mcp-server` entry point defined in `pyproject.toml`. It packages an MCP server that speaks to TiDB via the same client primitives, reinforcing modular reuse of the SDK.

### Supporting repositories

#### `tests/`

- Pytest suites organized by feature (auto embeddings, hybrid/fulltext/vector search, table DDL, transactions, etc.).
- Shared fixtures live in `tests/fixtures/`, while `tests/utils.py` contains helpers for TiDB clusters and temporary tables. Tests import from the published package root (`pytidb`) to validate the public API.

#### `examples/`

- Hands-on reference pipelines grouped by scenario (quickstart, RAG, hybrid search, memory, custom embeddings, multi-modal image search, realtime streams, etc.).
- Each directory contains executable scripts/notebooks that illustrate recommended wiring between `TiDBClient`, `TableModel`, embeddings, and rerankers.

#### `docs/`

- Houses the MkDocs documentation site declared as a dedicated uv workspace member (`[tool.uv.workspace]`). `mkdocs.yml`, `docs/src/`, and `docs/pyproject.toml` describe the site build; `docs/quickstart.ipynb` backs the README quick-start badge.
- Documentation changes often mirror SDK behavior, so update these files alongside `pytidb/` changes when behavior shifts.

#### Tooling & automation

- `pyproject.toml` configures project metadata, optional extras, dependency groups, pytest defaults, and Hatch build rules. Changing dependencies or CLI entry points should happen here.
- `uv.lock` captures the exact dependency graph used in CI (driven via `uv sync`).
- `Makefile` codifies the supported workflows (`install_dev`, `lint`, `test`, `build`, `publish`).
- `.github/workflows/` enforces lint/test/publish automation; `.devcontainer/` and `.vscode/` make sure contributors share the same editor/extensions.

### Code organization principles

- Prefer extending the declarative `TableModel`/`Table` abstractions instead of issuing raw SQL directly from new modules.
- Keep provider-specific logic (embeddings, rerankers, MCP, etc.) behind interfaces so optional dependencies remain isolated.
- Maintain parity between runtime modules, documentation (`docs/`), examples, and tests when shipping new features—each directory targets a distinct audience but relies on the same core APIs shown above.

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
