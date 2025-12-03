# How to contribute

Thank you for your interest in contributing to the TiDB Python SDK project!

## Project Structure Overview

This section provides an introduction to the core structure of the pytidb project to help new contributors understand the codebase organization.

### Directory Structure

```
pytidb/
├── pytidb/                    # Main source code package
│   ├── __init__.py           # Package initialization and main exports
│   ├── client.py             # TiDBClient - Main client class for database connections
│   ├── table.py              # Table - Core table operations and ORM functionality
│   ├── search.py             # Search implementations (vector, full-text, hybrid)
│   ├── schema.py             # Database schema definitions and models
│   ├── filters.py            # Query filtering and WHERE clause building
│   ├── fusion.py             # Hybrid search fusion algorithms
│   ├── sql.py                # SQL query building utilities
│   ├── result.py             # Query result handling and formatting
│   ├── utils.py              # General utility functions
│   ├── databases.py          # Database management functions
│   ├── datatype.py           # Data type definitions
│   ├── errors.py             # Custom exception classes
│   ├── logger.py             # Logging configuration
│   ├── base.py               # Base classes and registries
│   ├── py.typed              # PEP 561 typing marker
│   ├── embeddings/           # Embedding functionality
│   │   ├── base.py           # Base embedding classes
│   │   ├── builtin.py        # Built-in embedding models
│   │   ├── utils.py          # Embedding utilities
│   │   ├── dimensions.py     # Dimension management
│   │   └── aliases.py        # Model aliases
│   ├── orm/                  # ORM (Object-Relational Mapping) components
│   │   ├── indexes.py        # Index definitions (vector, full-text)
│   │   ├── vector.py         # Vector-specific ORM features
│   │   ├── distance_metric.py # Distance metric implementations
│   │   ├── functions.py      # SQL functions
│   │   ├── types.py          # Custom SQL types
│   │   ├── tiflash_replica.py # TiFlash replica management
│   │   ├── information_schema.py # Information schema utilities
│   │   ├── variables.py      # ORM configuration variables
│   │   └── sql/              # SQL generation modules
│   ├── rerankers/            # Result reranking functionality
│   │   ├── base.py           # Base reranker classes
│   │   └── litellm.py        # LiteLLM reranker integration
│   └── ext/                  # Extensions
│       └── mcp/              # Model Context Protocol support
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest configuration
│   ├── fixtures/             # Test fixtures
│   └── test_*.py             # Individual test modules
├── examples/                 # Example code and tutorials
│   ├── basic/                # Basic usage examples
│   ├── quickstart/           # Quick start guide
│   ├── vector_search/        # Vector search examples
│   ├── fulltext_search/      # Full-text search examples
│   ├── hybrid_search/        # Hybrid search examples
│   ├── auto_embedding/       # Auto-embedding examples
│   ├── custom_embedding/     # Custom embedding examples
│   ├── image_search/         # Image search examples
│   ├── rag/                  # RAG (Retrieval-Augmented Generation) examples
│   ├── memory/               # Memory management examples
│   └── text2sql/             # Text-to-SQL examples
└── docs/                     # Documentation
    ├── src/                  # Documentation source
    ├── mkdocs.yml            # MkDocs configuration
    └── quickstart.ipynb      # Jupyter notebook quickstart
```

### Core Modules and Their Purposes

#### Main Components

- **`TiDBClient` (client.py)**: The primary entry point for connecting to TiDB databases. Handles connection management, session context, and database operations.

- **`Table` (table.py)**: Core ORM class that provides high-level interface for table operations including CRUD operations, search functionality, and schema management.

- **`Search` (search.py)**: Implements various search algorithms including vector search, full-text search, and hybrid search with fusion capabilities.

#### Supporting Modules

- **`Schema` (schema.py)**: Defines database schema models, column types, and validation rules for tables.

- **`Filters` (filters.py)**: Provides query filtering capabilities with support for complex WHERE clauses and conditions.

- **`Fusion` (fusion.py)**: Implements algorithms for combining results from different search types (vector + full-text) in hybrid search scenarios.

- **`Embeddings` (embeddings/)**: Manages embedding generation with support for multiple models and providers, including built-in and custom embedding functions.

- **`ORM` (orm/)**: Contains ORM-specific functionality including index management, vector operations, and TiDB-specific features.

- **`Rerankers` (rerankers/)**: Provides result reranking capabilities to improve search relevance using various reranking models.

### Architecture Overview

The pytidb SDK follows a layered architecture:

1. **Client Layer**: `TiDBClient` provides the main interface for database connections and operations.

2. **Table/ORM Layer**: `Table` class provides high-level ORM functionality with support for both traditional SQL operations and AI-powered search.

3. **Search Layer**: Implements multiple search paradigms:
   - Vector search for semantic similarity
   - Full-text search for keyword matching
   - Hybrid search combining both approaches

4. **Embedding Layer**: Handles automatic embedding generation for text and multimodal data.

5. **Database Layer**: Interfaces with TiDB's MySQL-compatible protocol and leverages TiDB's vector and full-text index capabilities.

### Key Features Architecture

- **Multi-Modal Support**: The SDK supports text, images, and other data types through the embeddings system.
- **Flexible Indexing**: Supports both vector indexes for similarity search and full-text indexes for keyword search.
- **Transaction Support**: Full ACID transaction support through SQLAlchemy integration.
- **Extensible Design**: Plugin architecture for custom embeddings, rerankers, and search algorithms.

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

