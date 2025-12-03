# How to contribute

Thank you for your interest in contributing to the TiDB Python SDK project!

## Project Structure Overview

This section provides an overview of the core structure and organization of the PyTiDB project to help new contributors understand the codebase.

### Project Architecture

PyTiDB is a Python AI SDK for TiDB that provides unified search capabilities, automatic embeddings, and multi-modal data support. The project follows a modular architecture with clear separation of concerns.

### Directory Structure

```
pytidb/
├── pytidb/                    # Main package directory
│   ├── __init__.py           # Package initialization and main exports
│   ├── base.py               # Base classes and registry
│   ├── client.py             # TiDBClient - main client for database operations
│   ├── table.py              # Table class - core table operations and ORM
│   ├── search.py             # Search functionality (vector, fulltext, hybrid)
│   ├── schema.py             # Schema definitions and table models
│   ├── databases.py          # Database management utilities
│   ├── datatype.py           # Data type definitions
│   ├── errors.py             # Custom exception classes
│   ├── filters.py            # Query filtering functionality
│   ├── fusion.py             # Result fusion for hybrid search
│   ├── sql.py                # SQL query utilities
│   ├── utils.py              # General utility functions
│   ├── logger.py             # Logging configuration
│   ├── result.py             # Query result handling
│   ├── py.typed              # Type hint marker file
│   ├── embeddings/           # Embedding functionality
│   │   ├── base.py           # Base embedding classes
│   │   ├── builtin.py        # Built-in embedding functions
│   │   ├── utils.py          # Embedding utilities
│   │   ├── aliases.py        # Model aliases
│   │   └── dimensions.py     # Dimension management
│   ├── orm/                  # ORM components
│   │   ├── indexes.py        # Index definitions (vector, fulltext)
│   │   ├── distance_metric.py # Distance metrics for vector search
│   │   ├── vector.py         # Vector field support
│   │   ├── functions.py      # SQL functions
│   │   ├── types.py          # Custom SQL types
│   │   ├── information_schema.py # Information schema utilities
│   │   ├── tiflash_replica.py # TiFlash replica management
│   │   ├── variables.py      # Environment variables
│   │   ├── _typing.py        # Type definitions
│   │   └── sql/              # SQL generation
│   ├── rerankers/            # Result reranking functionality
│   └── ext/                  # Extensions
│       └── mcp/              # Model Context Protocol support
├── examples/                 # Example applications
│   ├── basic/                # Basic usage examples
│   ├── vector_search/        # Vector search examples
│   ├── fulltext_search/      # Fulltext search examples
│   ├── hybrid_search/        # Hybrid search examples
│   ├── image_search/         # Image search examples
│   ├── rag/                  # RAG (Retrieval-Augmented Generation)
│   ├── memory/               # Memory/chat examples
│   ├── text2sql/             # Text-to-SQL examples
│   ├── auto_embedding/       # Auto-embedding examples
│   ├── custom_embedding/     # Custom embedding examples
│   └── vector-search-with-realtime-data/ # Real-time data examples
├── tests/                    # Test suite
│   └── fixtures/             # Test fixtures and data
└── docs/                     # Documentation source
    └── src/                  # Documentation content
```

### Core Modules and Their Purposes

#### Main Components

- **TiDBClient (`client.py`)**: The primary client class for connecting to and interacting with TiDB. Handles database connections, session management, and provides the main entry point for all database operations.

- **Table (`table.py`)**: Core ORM class that represents database tables. Provides methods for CRUD operations, search functionality, and schema management. This is the main interface for table-level operations.

- **Search (`search.py`)**: Implements the unified search functionality including vector search, fulltext search, and hybrid search. Handles query processing and result retrieval.

- **Schema (`schema.py`)**: Defines the data models and schema structures. Provides the foundation for table creation and data validation.

#### Specialized Modules

- **Embeddings (`embeddings/`)**: Handles text and image embedding generation. Supports various embedding models and providers including OpenAI, Hugging Face, and custom models.

- **ORM (`orm/`)**: Contains database-specific components including index definitions, vector field support, distance metrics, and SQL generation utilities.

- **Rerankers (`rerankers/`)**: Provides result reranking functionality to improve search relevance using various reranking models.

- **Extensions (`ext/`)**: Additional functionality including Model Context Protocol (MCP) server support for integration with AI development tools.

### Key Features Architecture

1. **Unified Search**: The search module integrates vector, fulltext, and hybrid search capabilities into a single interface.

2. **Auto-Embedding**: The embeddings module automatically generates and manages vector embeddings for text and image data.

3. **Multi-Modal Support**: Built-in support for text, images, and other data types through specialized field types and processing functions.

4. **Transaction Management**: Full ACID transaction support through SQLAlchemy integration.

5. **Flexible Filtering**: Advanced filtering capabilities supporting various data types and query conditions.

### Development Workflow

The project uses modern Python development practices:

- **uv** for dependency management and virtual environments
- **ruff** for code formatting and linting
- **pytest** for testing with comprehensive test coverage
- **pre-commit** hooks for code quality
- **mypy** for type checking

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

