import os
import uuid
from typing import Generator

import pytest
from dotenv import load_dotenv

from pytidb import TiDBClient


@pytest.fixture(scope="session", autouse=True)
def env():
    print("Loading environment variables")
    load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def client(env) -> TiDBClient:
    """
    Create a TiDBClient connected to the test database.
    Recommend to use fresh_client instead for isolated tests.
    """

    return TiDBClient.connect(
        # database_url=os.getenv("TIDB_DATABASE_URL", None),
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
        database=os.getenv("TIDB_DATABASE", "test"),
        ensure_db=True,  # This will create the database if it doesn't exist
        # debug=True,
    )


@pytest.fixture()
def fresh_client() -> Generator[TiDBClient, None, None]:
    """
    Create a TiDBClient connected to a fresh test database.
    """

    unique_db_name = f"test_pytidb_{uuid.uuid4().hex[:8]}"

    c = TiDBClient.connect(
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
        database=unique_db_name,
        ensure_db=True,  # This will create the database if it doesn't exist
        # debug=True,
    )

    yield c

    # Cleanup: drop the test database when session ends
    try:
        c.drop_database(unique_db_name)
    except Exception as e:
        print(f"Warning: Failed to drop temp database {unique_db_name}: {e}")
