import os

from .client import TiDBClient
from .table import Table
from sqlmodel import Session
from sqlalchemy import create_engine

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = (
    "True" if os.getenv("LITELLM_LOCAL_MODEL_COST_MAP") is None else None
)
os.environ["LITELLM_LOG"] = "WARNING" if os.getenv("LITELLM_LOG") is None else None

__all__ = ["TiDBClient", "Table", "Session", "create_engine"]
