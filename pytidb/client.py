from contextlib import contextmanager
from contextvars import ContextVar
from typing import List, Literal, Optional, Type, Generator

from pydantic import PrivateAttr
import sqlalchemy
from sqlalchemy import (
    Executable,
    SelectBase,
    text,
    Result,
)
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.orm import Session, DeclarativeMeta

from pytidb.orm.variables import EMBED_PROVIDER_API_KEY_VARS
from pytidb.base import default_registry
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

    # Necessary connection parameters for use_database functionality
    _reconnect_params: dict = PrivateAttr()

    def __init__(self, db_engine: Engine, reconnect_params: dict):
        self._db_engine = db_engine
        self._identifier_preparer = self._db_engine.dialect.identifier_preparer
        self._reconnect_params = reconnect_params
        self._is_serverless = bool(
            TIDB_SERVERLESS_HOST_PATTERN.match(self._db_engine.url.host)
        )

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

        if host and TIDB_SERVERLESS_HOST_PATTERN.match(host):
            kwargs.setdefault("pool_recycle", 300)
            kwargs.setdefault("pool_pre_ping", True)
            kwargs.setdefault("pool_timeout", 10)

        db_engine = create_engine(url, echo=debug, **kwargs)
        reconnect_params = {
            # host, port, etc is not needed because they will be built into the URL.
            # url is also not needed because it is already in `db_engine`.
            "ensure_db": ensure_db,
            "debug": debug,
            **kwargs,
        }

        return cls(db_engine, reconnect_params)

    def disconnect(self) -> None:
        self._db_engine.dispose()

    @property
    def db_engine(self) -> Engine:
        return self._db_engine

    @property
    def is_serverless(self) -> bool:
        """Check if the client is connected to TiDB Serverless.

        Returns:
            True if connected to TiDB Serverless, False otherwise.
        """
        return self._is_serverless

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

    def current_database(self) -> Optional[str]:
        """Get the current database name.

        Returns:
            The name of the current database, or None if no database is selected.
        """
        stmt = text("SELECT DATABASE();")
        with self._db_engine.connect() as conn:
            result = conn.execute(stmt)
            return result.scalar()

    def use_database(self, database: str, *, ensure_db: Optional[bool] = False) -> None:
        """Switch to a different database.

        This method provides the same experience as if the database was specified
        when calling connect(). It creates a new engine with the specified database
        to ensure the database context persists across connection drops and reconnects.

        Warning: Existing sessions will be destroyed.

        Args:
            database: The name of the database to switch to.
            ensure_db: If True, create the database if it doesn't exist.

        Raises:
            Exception: If the database doesn't exist and ensure_db is False.
        """

        # TODO: Find some way to remove the restriction that old sessions will be destroyed.
        # Generally we should allow using `use_database` in a chainable way where it opens a new
        # "database session", for example, two lines below should be allowed to work simultaneously:
        # client.use_database(a).create_table()
        # client.use_database(b).create_table()

        if ensure_db and not self.has_database(database):
            self.create_database(database, if_exists="skip")
        elif not ensure_db and not self.has_database(database):
            raise ValueError(f"Database '{database}' does not exist")

        new_url = self._db_engine.url.set(database=database)

        # Attempt to create the new client first, only dispose and update attributes if successful
        new_client = TiDBClient.connect(
            url=new_url.render_as_string(hide_password=False),
            **self._reconnect_params,
        )

        # Now that new_client is successfully created, dispose the old engine and update all attributes
        self._db_engine.dispose()
        self._db_engine = new_client._db_engine
        self._identifier_preparer = new_client._db_engine.dialect.identifier_preparer
        self._reconnect_params = new_client._reconnect_params

    # Table Management API

    def create_table(
        self,
        *,
        schema: Optional[Type[TableModel]] = None,
        if_exists: Optional[Literal["raise", "overwrite", "skip"]] = "raise",
    ) -> Table:
        if if_exists == "raise":
            table = Table(schema=schema, client=self).create(if_exists="raise")
        elif if_exists == "overwrite":
            self.drop_table(schema.__tablename__, if_not_exists="skip")
            table = Table(schema=schema, client=self).create(if_exists="raise")
        elif if_exists == "skip":
            table = Table(schema=schema, client=self).create(if_exists="skip")
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
            table = Table(schema=table_model, client=self)
            return table

        return None

    def list_tables(self) -> List[str]:
        stmt = text("SHOW TABLES;")
        with self._db_engine.connect() as conn:
            result = conn.execute(stmt)
            return [row[0] for row in result]

    def has_table(self, table_name: str) -> bool:
        return sqlalchemy.inspect(self._db_engine).has_table(table_name)

    def drop_table(
        self,
        table_name: str,
        if_not_exists: Optional[Literal["raise", "skip"]] = "raise",
    ):
        if if_not_exists not in ["raise", "skip"]:
            raise ValueError(f"Invalid if_not_exists value: {if_not_exists}")

        self.open_table(table_name).drop(if_not_exists=if_not_exists)

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

    def configure_embedding_provider(
        self, provider: str, api_key: str
    ) -> SQLExecuteResult:
        if provider not in EMBED_PROVIDER_API_KEY_VARS.keys():
            raise ValueError(
                f"Unsupported configure api key for embedding provider: {provider}"
            )

        var_name = EMBED_PROVIDER_API_KEY_VARS[provider]
        escape_var_name = self._identifier_preparer.quote(var_name)
        return self.execute(text(f"SET @@GLOBAL.{escape_var_name} = '{api_key}';"))

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
