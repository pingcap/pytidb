import os

from sqlmodel import Session
from sqlalchemy import create_engine
from sqlalchemy.dialects import registry

from .client import TiDBClient
from .table import Table
from .utils import build_tidb_connection_url
from .orm.dialects.tidb import TiDBDialect
from .orm.tiflash_repilica import TiFlashReplica

# Register the TiDB dialect with SQLAlchemy
registry.register("tidb", "pytidb.orm.dialects.tidb", "TiDBDialect")
registry.register("tidb.pymysql", "pytidb.orm.dialects.tidb", "TiDBDialect")

if "LITELLM_LOCAL_MODEL_COST_MAP" not in os.environ:
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"

if "LITELLM_LOG" not in os.environ:
    os.environ["LITELLM_LOG"] = "WARNING"


__all__ = [
    "TiDBDialect",
    "TiDBClient",
    "Table",
    "TiFlashReplica",
    "build_tidb_connection_url",
    "Session",
    "create_engine",
]
