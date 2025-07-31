import os
import uuid
import logging
from typing import Generator

import pytest
from dotenv import load_dotenv

from pytidb import TiDBClient
from pytidb.embeddings import EmbeddingFunction

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session", autouse=True)
def env():
    print("Loading environment variables")
    load_dotenv("tests/.env")


def create_tidb_client(database: str) -> TiDBClient:
    return TiDBClient.connect(
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
        database=database,
        ensure_db=True,  # This will create the database if it doesn't exist
        debug=os.getenv("TIDB_CLIENT_DEBUG", "false").lower() in ("true", "1", "yes"),
    )


def generate_db_name(prefix: str = "test_pytidb") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session", autouse=True)
def shared_client(env) -> Generator[TiDBClient, None, None]:
    """
    Create a shared TiDBClient instance that persists across multiple test functions.

    A test database will be created before the tests start and dropped
    after all tests complete.
    """
    db_name = generate_db_name()
    tidb_client = create_tidb_client(db_name)
    print(f"Shared client created for database {db_name}")

    yield tidb_client

    try:
        tidb_client.drop_database(db_name)
        tidb_client.disconnect()
    except Exception as e:
        logger.error(f"Failed to drop test database {db_name}: {e}")


@pytest.fixture()
def isolated_client(env) -> Generator[TiDBClient, None, None]:
    """
    Create an isolated TiDBClient instance that exists only for the lifetime of a single test function.

    A test database will be created before the test function starts and dropped
    after the test function completes.
    """
    db_name = generate_db_name()
    client = create_tidb_client(db_name)

    yield client

    try:
        client.drop_database(db_name)
        client.disconnect()
    except Exception as e:
        logger.error(f"Failed to drop test database {db_name}: {e}")


@pytest.fixture(scope="session", autouse=True)
def text_embed():
    return EmbeddingFunction("openai/text-embedding-3-small", timeout=20)
