from contextlib import contextmanager
from contextvars import ContextVar
from typing import List, Literal, Optional, Type, Generator

from pydantic import PrivateAttr
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

from pytidb.base import Base, default_registry
from pytidb.databases import create_database, database_exists
from pytidb.schema import TableModel
from pytidb.table import Table
from pytidb.utils import (
    TIDB_SERVERLESS_HOST_PATTERN,
    build_tidb_connection_url,
    create_engine_without_db,
)
from pytidb.logger import logger
from pytidb.result import SQLExecuteResult, SQLQueryResult


SESSION = ContextVar[Session | None]("session", default=None)


class TiDBClient:
    _db_engine: Engine = PrivateAttr()
    _inspector: Inspector = PrivateAttr()

    def __init__(self, db_engine: Engine):
        self._db_engine = db_engine
        self._inspector = sqlalchemy.inspect(self._db_engine)
        self._identifier_preparer = self._db_engine.dialect.identifier_preparer

    # TODO: Better typing for kwargs, including what's supported by pymysql and SQLAlchemy.
    @classmethod
    def connect(
        cls,
        url: Optional[str] = None,
        *,
        host: Optional[str] = "localhost",
        port: Optional[int] = 4000,
        username: Optional[str] = "root",
        password: Optional[str] = "",
        database: Optional[str] = "test",
        enable_ssl: Optional[bool] = None,
        ensure_db: Optional[bool] = False,
        debug: Optional[bool] = None,
        **kwargs,
    ) -> "TiDBClient":
        if url is None:
            url = build_tidb_connection_url(
                host=host,
                port=port,
                username=username,
                password=password,
                database=database,
                enable_ssl=enable_ssl,
            )
            # TODO: When URL is passed in directly, it should be validated.

        if ensure_db:
            try:
                temp_engine = create_engine_without_db(url, echo=debug, **kwargs)
                if not database_exists(temp_engine, database):
                    create_database(temp_engine, database)
            except Exception as e:
                logger.error("Failed to ensure database exists: %s", str(e))
                raise

        if kwargs.get("pool_recycle") is None and kwargs.get("pool_pre_ping") is None:
            if host and TIDB_SERVERLESS_HOST_PATTERN.match(host):
                kwargs["pool_recycle"] = 300
                kwargs["pool_pre_ping"] = True

        db_engine = create_engine(url, echo=debug, **kwargs)

        return cls(db_engine)

    def disconnect(self) -> None:
        self._db_engine.dispose()

    @property
    def db_engine(self) -> Engine:
        return self._db_engine

    # Database Management API

    def create_database(
        self, name: str, if_exists: Optional[Literal["raise", "skip"]] = "raise"
    ):
        return create_database(self._db_engine, name, if_exists=if_exists)

    def drop_database(self, name: str):
        db_name = self._identifier_preparer.quote(name)
        with self._db_engine.connect() as conn:
            stmt = text(f"DROP DATABASE IF EXISTS {db_name};")
            return conn.execute(stmt)

    def list_databases(self) -> List[str]:
        stmt = text("SHOW DATABASES;")
        with self._db_engine.connect() as conn:
            result = conn.execute(stmt)
            return [row[0] for row in result]

    def has_database(self, name: str) -> bool:
        return database_exists(self._db_engine, name)

    # Table Management API

    def create_table(
        self,
        *,
        schema: Optional[Type[TableModel]] = None,
        if_exists: Optional[Literal["raise", "overwrite", "skip"]] = "raise",
    ) -> Table:
        if if_exists == "raise":
            table = Table(schema=schema, client=self, if_exists="raise")
        elif if_exists == "overwrite":
            self.drop_table(schema.__tablename__, if_not_exists="skip")
            table = Table(schema=schema, client=self)
        elif if_exists == "skip":
            table = Table(schema=schema, client=self, if_exists="skip")
        else:
            raise ValueError(f"Invalid if_exists value: {if_exists}")
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
            table = Table(schema=table_model, client=self, if_exists="skip")
            return table

        return None

    def list_tables(self) -> List[str]:
        stmt = text("SHOW TABLES;")
        with self._db_engine.connect() as conn:
            result = conn.execute(stmt)
            return [row[0] for row in result]

    def has_table(self, table_name: str) -> bool:
        return self._inspector.has_table(table_name)

    def drop_table(
        self,
        table_name: str,
        if_not_exists: Optional[Literal["raise", "skip"]] = "raise",
    ):
        if if_not_exists not in ["raise", "skip"]:
            raise ValueError(f"Invalid if_not_exists value: {if_not_exists}")

        table = sqlalchemy.Table(
            table_name, Base.metadata, autoload_with=self._db_engine
        )
        return table.drop(self._db_engine, checkfirst=(if_not_exists == "skip"))

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
