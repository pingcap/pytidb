# PyTiDB Quickstart Example

This example demonstrates how to use the PyTiDB Python SDK to connect to a TiDB database, create a table, insert data, perform semantic search, and clean up resources.

## Prerequisites

- Python 3.8+
- Access to a TiDB cluster (TiDB Cloud or self-managed)
- OpenAI API key (for embedding)

## Setup

1. **Clone the repository and navigate to this directory:**

```bash
cd examples/quickstart
```

2. **Create and activate a virtual environment (recommended):**

```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Create a `.env` file in this directory and fill in your credentials:**

```ini
# .env example
TIDB_HOST=your_tidb_host
TIDB_PORT=4000
TIDB_USERNAME=your_tidb_username
TIDB_PASSWORD=your_tidb_password
TIDB_DATABASE=your_tidb_database
OPENAI_API_KEY=your_openai_api_key
```

## Running the Example

After completing the setup and filling in your `.env` file, run:

```bash
python main.py
```

You should see query and semantic search results printed in the console.

## Notes
- The script will create and drop a table named `chunks` in your database.
- Make sure your TiDB user has the necessary privileges.
- For more information, see the [PyTiDB documentation](https://github.com/pingcap/pytidb). 