import os

from sqlmodel import Session
from sqlalchemy import create_engine

from .client import TiDBClient
from .table import Table
from .utils import build_tidb_connection_url


if "LITELLM_LOCAL_MODEL_COST_MAP" not in os.environ:
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

if "LITELLM_LOG" not in os.environ:
    os.environ["LITELLM_LOG"] = "WARNING"


__all__ = [
    "TiDBClient",
    "Table",
    "build_tidb_connection_url",
    "Session",
    "create_engine",
]
