from contextlib import contextmanager
from contextvars import ContextVar
from typing import List, Optional, Type, Generator

from pydantic import PrivateAttr, BaseModel
import sqlalchemy
from sqlalchemy import Executable, SelectBase, text, Result
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session

from pytidb.base import default_registry
from pytidb.schema import TableModel, Field
from pytidb.table import Table
from pytidb.utils import build_tidb_dsn
from pytidb.logger import logger


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


SESSION = ContextVar[Session | None]("session", default=None)


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
        debug: Optional[bool] = None,
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

        db_engine = create_engine(database_url, echo=debug, **kwargs)

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
        table = Table(schema=schema, client=self)
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
            client=self,
        )

    def table_names(self) -> List[str]:
        return self._inspector.get_table_names()

    def has_table(self, table_name: str) -> bool:
        return self._inspector.has_table(table_name)

    def drop_table(self, table_name: str):
        table_name = self._db_engine.dialect.identifier_preparer.quote(table_name)
        return self.execute(f"DROP TABLE IF EXISTS {table_name}")

    def execute(
        self,
        sql: str | Executable,
        params: Optional[dict] = None,
        raise_error: Optional[bool] = False,
    ) -> SQLExecuteResult:
        try:
            with self.session() as session:
                if isinstance(sql, str):
                    stmt = text(sql)
                else:
                    stmt = sql
                result: Result = session.execute(stmt, params or {})
                return SQLExecuteResult(rowcount=result.rowcount, success=True)
        except Exception as e:
            if raise_error:
                raise e
            logger.error(f"Failed to execute SQL: {str(e)}")
            return SQLExecuteResult(rowcount=0, success=False, message=str(e))

    def query(
        self,
        sql: str | SelectBase,
        params: Optional[dict] = None,
    ) -> SQLQueryResult:
        with self.session() as session:
            if isinstance(sql, str):
                stmt = text(sql)
            else:
                stmt = sql
            result = session.execute(stmt, params)
            return SQLQueryResult(result)

    def disconnect(self) -> None:
        self._db_engine.dispose()

    @contextmanager
    def session(
        self, *, provided_session: Optional[Session] = None, **kwargs
    ) -> Generator[Session, None, None]:
        if provided_session is not None:
            session = provided_session
            is_local_session = False
        elif SESSION.get() is not None:
            session = SESSION.get()
            is_local_session = False
        else:
            # Since both the TiDB Client and Table API begin a Session within the method, the Session ends when
            # the method returns. The error: "Parent instance <x> is not bound to a Session;" will show when accessing
            # the returned object. To prevent it, we set the expire_on_commit parameter to False by default.
            # Details: https://sqlalche.me/e/20/bhk3
            kwargs.setdefault("expire_on_commit", False)
            session = Session(self._db_engine, **kwargs)
            SESSION.set(session)
            is_local_session = True

        try:
            yield session
            if is_local_session:
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            if is_local_session:
                session.close()
                SESSION.set(None)
