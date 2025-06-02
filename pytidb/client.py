from contextlib import contextmanager
from contextvars import ContextVar
from typing import List, Optional, Type, Generator

from pydantic import PrivateAttr, BaseModel
import sqlalchemy
from sqlalchemy import (
    Executable,
    Inspector,
    SelectBase,
    text,
    Result,
)
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session, DeclarativeMeta

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
    _inspector: Inspector = PrivateAttr()

    def __init__(self, db_engine: Engine):
        self._db_engine = db_engine
        self._inspector = sqlalchemy.inspect(self._db_engine)
        self._identifier_preparer = self._db_engine.dialect.identifier_preparer

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

    def disconnect(self) -> None:
        self._db_engine.dispose()

    @property
    def db_engine(self) -> Engine:
        return self._db_engine

    # Database Management API

    def create_database(self, name: str, skip_exists: bool = True):
        db_name = self._identifier_preparer.quote(name)
        with self._db_engine.connect() as conn:
            if skip_exists:
                stmt = text(f"CREATE DATABASE IF NOT EXISTS {db_name};")
            else:
                stmt = text(f"CREATE DATABASE {db_name};")
            return conn.execute(stmt)

    def drop_database(self, name: str) -> bool:
        db_name = self._identifier_preparer.quote(name)
        with self._db_engine.connect() as conn:
            stmt = text(f"DROP DATABASE IF EXISTS {db_name};")
            result = conn.execute(stmt)
        return result.rowcount > 0

    def database_names(self) -> List[str]:
        stmt = text("SHOW DATABASES;")
        with self._db_engine.connect() as conn:
            result = conn.execute(stmt)
            return [row[0] for row in result]

    def has_database(self, name: str) -> bool:
        return name in self.database_names()

    # Table Management API

    def create_table(self, *, schema: Optional[Type[TableModel]] = None) -> Table:
        table = Table(schema=schema, client=self)
        return table

    def _get_table_model(self, table_name: str) -> Optional[Type[DeclarativeMeta]]:
        for m in default_registry.mappers:
            if m.persist_selectable.name == table_name:
                return m.class_
        return None

    def open_table(self, table_name: str) -> Optional[Table]:
        # If the table in the mapper registry.
        table_model = self._get_table_model(table_name)
        if table_model is not None:
            table = Table(schema=table_model, client=self)
            return table

        return None

    def table_names(self) -> List[str]:
        return self._inspector.get_table_names()

    def has_table(self, table_name: str) -> bool:
        return self._inspector.has_table(table_name)

    def drop_table(self, table_name: str) -> bool:
        return self._inspector.drop_table(table_name)

    # Raw SQL API

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

    # Session API

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
