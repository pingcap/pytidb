import os

import pytest
from dotenv import load_dotenv

from pytidb import TiDBClient


@pytest.fixture(scope="session", autouse=True)
def env():
    print("Loading environment variables")
    load_dotenv()


@pytest.fixture(scope="session", autouse=True)
def db(env) -> TiDBClient:
    return TiDBClient.connect(
        host=os.getenv("TIDB_HOST", "localhost"),
        port=int(os.getenv("TIDB_PORT", "4000")),
        username=os.getenv("TIDB_USERNAME", "root"),
        password=os.getenv("TIDB_PASSWORD", ""),
    )
