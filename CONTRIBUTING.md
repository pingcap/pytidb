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

Understanding where each concern lives lets you jump from idea to PR without
guesswork. Use the quick tree for bearings, then dive deeper via the sections
below.

### Visual snapshot

```text
.
├── pyproject.toml         # Workspace + package metadata and scripts
├── uv.lock                # Reproducible dependency lockfile
├── Makefile               # install/lint/test/build helpers
├── pytidb/                # Core SDK (clients, schemas, search, embeddings)
├── tests/                 # Pytest suites, fixtures, and utilities
├── docs/                  # MkDocs workspace member with docs-only deps
├── examples/              # End-to-end notebooks and scripts
└── README.md, CONTRIBUTING.md, LICENSE, CLAUDE.md, .gitignore, etc.
```

### Core areas (what & why)

<details>
<summary><strong><code>pytidb/</code> – SDK runtime</strong></summary>

- `client.py`, `databases.py`, and `utils.py` coordinate TiDB connections,
  `TiDBClient.run()`, auto database creation, and context-managed sessions.
- `table.py`, `schema.py`, and `orm/` translate SQLModel definitions into live
  TiDB tables, vector/text indexes, and query builders used throughout the SDK.
- `search.py`, `embeddings/`, and `rerankers/` implement vector, hybrid, and
  reranked search flows, while `sql.py` re-exports SQL primitives for callers.
- `ext/mcp/` wires the `tidb-mcp-server` console script so the SDK can run as a
  Model Context Protocol data source.
- Everything under `pytidb/` ships in the final wheel—changes here affect users
  directly, so pair edits with tests and docs.

</details>

<details>
<summary><strong><code>tests/</code> – Regression safety net</strong></summary>

- Feature-focused suites (`tests/test_table.py`, `tests/test_search.py`, etc.)
  validate tables, schema helpers, hybrid search, embeddings, and ORM utilities.
- Shared fixtures (`tests/fixtures/`) spin up TiDB tables, sample data, and
  fake embeddings; `tests/utils.py` covers helper assertions.
- Run `uv run pytest` or `make test` (parallel-friendly via pytest-xdist) to
  confirm behavior before submitting PRs.

</details>

<details>
<summary><strong><code>docs/</code> – MkDocs site</strong></summary>

- Independent uv workspace member with its own `pyproject.toml` for MkDocs
  dependencies, plus `mkdocs.yml` for navigation, theme, and plugins.
- `docs/src/` houses Markdown sources, notebooks, assets, and redirects used on
  pingcap.github.io; `docs/src/index.md` is the entry point.
- Use `uv run --project docs mkdocs serve` (or `uv run mkdocs serve` inside
  `docs/`) to preview changes when touching documentation.

</details>

<details>
<summary><strong><code>examples/</code> – Runnable playbook</strong></summary>

- Directories map to real workflows: `basic/`, `auto_embedding/`,
  `custom_embedding/`, `hybrid_search/`, `vector_search/`, `rag/`, `memory/`,
  `text2sql/`, `image_search/`, and
  `vector-search-with-realtime-data/` (shared media in `examples/assets/`).
- Scripts and notebooks import the public SDK (`from pytidb import TiDBClient,
  Table`) to showcase best practices; mirror this structure when adding new
  samples.

</details>

### Practical scenarios (where to work)

1. **Extend the search pipeline**
   - Touch `pytidb/search.py` to add planner logic or reranker hooks.
   - Update supporting utilities (`pytidb/embeddings/`, `pytidb/rerankers/`, or
     `pytidb/orm/sql/ddl.py`) if the change alters indexes or scoring.
   - Reproduce with `examples/hybrid_search/` or `examples/vector_search/`, then
     assert via `tests/test_search.py`.
2. **Add a new SDK feature**
   - Model-level changes start in `pytidb/schema.py` / `pytidb/orm/`; runtime
     behavior lands in `pytidb/table.py` or `pytidb/client.py`.
   - Document the addition in `docs/src/` (API reference) and `README.md`, and
     surface a runnable illustration in `examples/` if applicable.
   - Cover behavior with focused tests (e.g., `tests/test_table.py`) and any new
     fixtures needed under `tests/fixtures/`.
3. **Document or teach a workflow**
   - Prototype the flow in `examples/` (new folder plus notebook/script) to keep
     runnable artifacts close to the code.
   - Port the narrative to `docs/src/guide/...` or `docs/src/tutorials/...` and
     link to the example; use `uv run --project docs mkdocs serve` to preview.
   - Cross-reference from `README.md` or `docs/src/index.md` so contributors can
     find the new material.

### Quick reference

| Directory/File | Why it matters | Typical edits |
| --- | --- | --- |
| `pytidb/` | Production SDK modules (client, table, search, embeddings, ORM, MCP) | Feature work, bugfixes, new integrations |
| `tests/` | Pytest coverage, fixtures, TiDB provisioning utilities | Regression tests, fixtures, helper assertions |
| `docs/` | MkDocs site + assets (workspace member) | Tutorial/API updates, site config tweaks |
| `examples/` | Runnable notebooks/scripts showcasing SDK scenarios | New workflow demos, repro cases, tutorial assets |
| `pyproject.toml` / `uv.lock` | Build metadata, dependencies, CLI entry points | Release prep, dependency bumps, console scripts |
| `Makefile` | Single entry for install/lint/test/build commands | Local workflow automation, CI parity |
| `README.md` / `CONTRIBUTING.md` | High-level onboarding content | Quickstart guidance, contribution policies |

## Navigating the Codebase

Use the guide below to jump directly to the files and directories that matter
for common contribution scenarios.

### Where do I go to add a new feature to the ORM?

- Extend TiDB-aware column types, indexes, or SQL helpers inside
  `pytidb/orm/` (e.g., `types.py`, `indexes.py`, `sql/ddl.py`).
- Wire new behavior into `pytidb/schema.py` (model metaclass + field helpers)
  and `pytidb/table.py` so schemas and runtime tables pick up your change.
- Cover the feature with tests under `tests/test_schema.py`,
  `tests/test_table.py`, or a new targeted `tests/test_*.py`.

### Where do I go to fix a bug in vector search?

- Start with `pytidb/search.py`, which builds search plans, rerankers, and
  filters, and trace how `Table.search()` in `pytidb/table.py` invokes it.
- Validate distance calculations and index usage under `pytidb/orm/` and
  reranker hooks in `pytidb/rerankers/` if scores feel off.
- To add embedding functionality, look in `pytidb/embeddings/` where providers
  register encoders, dimensions, and server/client routing.
- Reproduce issues with `examples/vector_search/` or `examples/hybrid_search/`
  and lock fixes in via `tests/test_search.py` (plus fixtures in
  `tests/fixtures/` when needed).

### Where do I go to add a new example?

- Create a directory beneath `examples/` (follow existing folders such as
  `examples/basic/`, `examples/rag/`, or `examples/vector_search/`) and include
  runnable notebooks/scripts plus any media in `examples/assets/`.
- Reference shared helper code under `examples/` instead of duplicating client
  setup, and link the new example from `README.md` or docs copy as appropriate.

### Where do I go to update documentation?

- The bundled MkDocs site lives in `docs/` with `docs/mkdocs.yml` defining
  navigation and `docs/src/` storing Markdown content and assets.
- Because `docs/src/index.md` currently redirects contributors to
  [`pingcap/pingcap.github.io`](https://github.com/pingcap/pingcap.github.io),
  send larger docs changes there, while quickstart tweaks or internal notes can
  still be edited in this repo.
- Use `uv run mkdocs serve` (from the `docs/` directory) to preview changes if
  you touch MkDocs content.

### Where do I go to add or modify tests?

- Unit and integration coverage sits in `tests/`, with shared fixtures in
  `tests/fixtures/`, utilities in `tests/utils.py`, and TiDB provisioning hooks
  in `tests/conftest.py`.
- Follow the pattern established by nearby files (e.g., `tests/test_table.py`,
  `tests/test_search.py`) and run `uv run pytest` or `make test` before opening
  a pull request.

### Where do I go to understand the client architecture?

- `pytidb/client.py` manages connections, sessions, and higher-level helpers,
  while `pytidb/table.py` translates `TableModel` definitions from
  `pytidb/schema.py` into live TiDB tables.
- Trace query planning flows in `pytidb/search.py`, data-type and index
  metadata in `pytidb/orm/`, and connection utilities in `pytidb/databases.py`
  or `pytidb/utils.py`.
- Walk through `examples/basic/` or `examples/auto_embedding/` alongside the
  README to see how these modules collaborate from client creation to query
  execution.
