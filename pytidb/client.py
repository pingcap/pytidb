import logging
from typing import List, Optional, Type

from pydantic import PrivateAttr, BaseModel
import sqlalchemy
from sqlalchemy import text, Result
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session

from pytidb.base import default_registry
from pytidb.schema import TableModel, Field
from pytidb.table import Table
from pytidb.utils import build_tidb_dsn

logger = logging.getLogger(__name__)


class SQLExecuteResult(BaseModel):
    rowcount: int = Field(0)
    success: bool = Field(False)
    message: Optional[str] = Field(None)


class SQLQueryResult:
    _result: Result

    def __init__(self, result):
        self._result = result

    def scalar(self):
        return self._result.scalar()

    def one(self):
        return self._result.one()

    def to_rows(self):
        return self._result.fetchall()

    def to_pandas(self):
        try:
            import pandas as pd
        except Exception:
            raise ImportError(
                "Failed to import pandas, please install it with `pip install pandas`"
            )
        keys = self._result.keys()
        rows = self._result.fetchall()
        return pd.DataFrame(rows, columns=keys)

    def to_list(self) -> List[dict]:
        keys = self._result.keys()
        rows = self._result.fetchall()
        return [dict(zip(keys, row)) for row in rows]

    def to_pydantic(self, model: Type[BaseModel]) -> List[BaseModel]:
        ls = self.to_list()
        return [model.model_validate(item) for item in ls]


class TiDBClient:
    _db_engine: Engine = PrivateAttr()

    def __init__(self, db_engine: Engine):
        self._db_engine = db_engine
        self._inspector = sqlalchemy.inspect(self._db_engine)

    @classmethod
    def connect(
        cls,
        database_url: Optional[str] = None,
        *,
        host: Optional[str] = "localhost",
        port: Optional[int] = 4000,
        username: Optional[str] = "root",
        password: Optional[str] = "",
        database: Optional[str] = "test",
        enable_ssl: Optional[bool] = None,
        **kwargs,
    ) -> "TiDBClient":
        if database_url is None:
            database_url = str(
                build_tidb_dsn(
                    host=host,
                    port=port,
                    username=username,
                    password=password,
                    database=database,
                    enable_ssl=enable_ssl,
                )
            )

        db_engine = create_engine(database_url, **kwargs)
        return cls(db_engine)

    # Notice: Since the Vector type is not in the type support list of mysql dialect, using the reflection API will cause an error.
    # https://github.com/sqlalchemy/sqlalchemy/blob/d6f11d9030b325d5afabf87869a6e3542edda54b/lib/sqlalchemy/dialects/mysql/base.py#L1199
    # def _load_table_metadata(self, table_names: Optional[List[str]] = None):
    #     if not table_names:
    #         Base.metadata.reflect(bind=self._db_engine)
    #     else:
    #         Base.metadata.reflect(bind=self._db_engine, only=table_names, extend_existing=True)

    @property
    def db_engine(self) -> Engine:
        return self._db_engine

    def create_table(self, *, schema: Optional[Type[TableModel]] = None) -> Table:
        table = Table(schema=schema, db_engine=self._db_engine)
        return table

    def get_table_model(self, table_name: str):
        for m in default_registry.mappers:
            if m.persist_selectable.name == table_name:
                return m.class_

    def open_table(self, table_name: str) -> Optional[Table]:
        table_model = self.get_table_model(table_name)
        if table_model is None:
            return None
        return Table(
            schema=table_model,
            db_engine=self._db_engine,
        )

    def table_names(self) -> List[str]:
        return self._inspector.get_table_names()

    def has_table(self, table_name: str) -> bool:
        return self._inspector.has_table(table_name)

    def drop_table(self, table_name: str):
        return self.execute(f"DROP TABLE IF EXISTS {table_name}")

    def execute(
        self,
        sql: str,
        params: Optional[dict] = None,
        raise_error: Optional[bool] = False,
    ) -> SQLExecuteResult:
        with Session(self._db_engine) as session:
            try:
                result: Result = session.execute(text(sql), params or {})
                session.commit()
                return SQLExecuteResult(rowcount=result.rowcount, success=True)
            except Exception as e:
                session.rollback()
                if raise_error:
                    raise e
                logger.error(f"Failed to execute SQL: {str(e)}")
                return SQLExecuteResult(rowcount=0, success=False, message=str(e))

    def query(
        self,
        sql: str,
        params: Optional[dict] = None,
    ) -> SQLQueryResult:
        with Session(self._db_engine) as session:
            result = session.execute(sqlalchemy.text(sql), params)
            return SQLQueryResult(result)

    def disconnect(self) -> None:
        self._db_engine.dispose()
