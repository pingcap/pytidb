import os

from sqlmodel import Session
from sqlalchemy import create_engine

from .client import TiDBClient
from .table import Table
from .utils import build_tidb_connection_url

# Import async classes
from .async_client import AsyncTiDBClient, AsyncConnection
from .async_table import AsyncTable
from .async_result import AsyncQueryResult, AsyncSQLQueryResult, AsyncSQLExecuteResult

if "LITELLM_LOCAL_MODEL_COST_MAP" not in os.environ:
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

if "LITELLM_LOG" not in os.environ:
    os.environ["LITELLM_LOG"] = "WARNING"


__all__ = [
    # Synchronous API (existing)
    "TiDBClient",
    "Table",
    "build_tidb_connection_url",
    "Session",
    "create_engine",
    # Asynchronous API (new)
    "AsyncTiDBClient",
    "AsyncConnection",
    "AsyncTable",
    "AsyncQueryResult",
    "AsyncSQLQueryResult",
    "AsyncSQLExecuteResult",
]
