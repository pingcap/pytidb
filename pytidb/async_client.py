"""Asyncio support for PyTiDB using wrapper pattern with thread pool.

This module provides an async API layer that wraps the existing synchronous
TiDBClient without breaking the sync API. All synchronous operations are
offloaded to a thread pool using asyncio.to_thread().

Example:
    import asyncio
    from pytidb.async_client import AsyncTiDBClient

    async def main():
        async with AsyncTiDBClient.connect(
            host="localhost",
            port=4000,
            username="root",
            password="",
            database="test"
        ) as client:
            result = await client.query("SELECT * FROM users")
            print(result.to_list())

    asyncio.run(main())
"""

import asyncio
from typing import List, Literal, Optional, Type, Any

from sqlalchemy import Executable, SelectBase

from pytidb.client import TiDBClient
from pytidb.result import SQLExecuteResult, SQLQueryResult
from pytidb.table import Table
from pytidb.schema import TableModel


class _AsyncClientContext:
    """Context manager factory for AsyncTiDBClient.

    This class handles the creation and cleanup of AsyncTiDBClient instances
    when used with `async with AsyncTiDBClient.connect(...)`. It delays the
    actual connection creation until __aenter__ is called.
    """

    def __init__(self, cls, connection_kwargs):
        """Initialize the context manager factory.

        Args:
            cls: The AsyncTiDBClient class.
            connection_kwargs: Keyword arguments for connection.
        """
        self._cls = cls
        self._connection_kwargs = connection_kwargs
        self._client = None

    async def __aenter__(self):
        """Create and return the AsyncTiDBClient instance.

        Returns:
            AsyncTiDBClient instance ready for async operations.
        """
        self._client = await self._cls.connect_async(**self._connection_kwargs)
        return self._client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the AsyncTiDBClient instance.

        Automatically disconnects from the database when exiting the context.
        Connection is closed even if an exception occurs.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        if self._client is not None:
            await self._client.disconnect()


class AsyncSQLQueryResult:
    """Async query result with materialized data for thread safety.

    This class wraps materialized query results to ensure thread safety.
    All database operations happen in the initial thread, and only Python
    data structures are returned. This avoids sharing SQLAlchemy Result
    objects across threads, which is not thread-safe.

    The data is fully materialized during query execution, so subsequent
    method calls do not access the database or require additional thread
    pool operations.

    Example:
        result = await client.query("SELECT * FROM users")
        rows = await result.to_list()
        df = await result.to_pandas()
    """

    def __init__(self, rows: List[dict], keys: Optional[List[str]] = None, scalar_val: Optional[Any] = None):
        """Initialize with materialized result data.

        Args:
            rows: List of dictionaries representing query results.
            keys: Column names (for pandas conversion).
            scalar_val: Pre-computed scalar value if this is a scalar query.
        """
        self._rows = rows
        self._keys = keys or (list(rows[0].keys()) if rows else [])
        self._scalar_val = scalar_val

    async def to_list(self) -> List[dict]:
        """Return query results as a list of dictionaries.

        Returns:
            List of dictionaries representing the query results.

        Example:
            rows = await result.to_list()
            for row in rows:
                print(row)
        """
        return self._rows

    async def scalar(self):
        """Return the pre-computed scalar value.

        Returns:
            The scalar value (first column of first row).

        Example:
            count = await result.scalar()
        """
        return self._scalar_val

    async def to_pandas(self):
        """Convert query results to a pandas DataFrame.

        Returns:
            pandas DataFrame with query results.

        Example:
            df = await result.to_pandas()
        """
        try:
            import pandas as pd
        except ImportError:
            raise ImportError(
                "Failed to import pandas, please install it with `pip install pandas`"
            )
        return pd.DataFrame(self._rows, columns=self._keys)

    async def to_pydantic(self, model: Type):
        """Convert query results to a list of pydantic models.

        Args:
            model: Pydantic model class to convert to.

        Returns:
            List of pydantic model instances.

        Example:
            from pydantic import BaseModel

            class User(BaseModel):
                id: int
                name: str

            users = await result.to_pydantic(User)
        """
        return [model.model_validate(row) for row in self._rows]


class AsyncTiDBClient:
    """Async wrapper for TiDBClient using asyncio.to_thread().

    This class provides an async API by wrapping synchronous TiDB operations
    and executing them in a thread pool. It maintains all the functionality
    of the sync TiDBClient while providing async/await syntax.

    All database operations are thread-safe since each operation uses
    SQLAlchemy's session context manager under the hood.

    Example:
        # Using async context manager (recommended)
        async with AsyncTiDBClient.connect(
            host="localhost", port=4000, database="test"
        ) as client:
            result = await client.query("SELECT * FROM users")

        # Or create client directly
        client = await AsyncTiDBClient.connect_async(
            host="localhost", port=4000, database="test"
        )
        try:
            result = await client.query("SELECT * FROM users")
        finally:
            await client.disconnect()
    """

    def __init__(self, sync_client: TiDBClient):
        """Initialize with a synchronous TiDBClient instance.

        Args:
            sync_client: The synchronous TiDBClient to wrap.
        """
        self._sync_client = sync_client

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
    ) -> _AsyncClientContext:
        """Create a context manager for async connection to TiDB.

        This method returns a context manager that creates the async connection
        when entering and automatically disconnects when exiting. This is the
        recommended way to use AsyncTiDBClient.

        Args:
            url: Connection URL. If None, constructed from other parameters.
            host: Database host (default: localhost).
            port: Database port (default: 4000).
            username: Database username (default: root).
            password: Database password (default: empty).
            database: Database name (default: test).
            enable_ssl: Enable SSL connection.
            ensure_db: Create database if it doesn't exist.
            debug: Enable debug mode.
            **kwargs: Additional arguments passed to SQLAlchemy create_engine().

        Returns:
            _AsyncClientContext instance that can be used with `async with`.

        Example:
            async with AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="mydb"
            ) as client:
                result = await client.query("SELECT * FROM users")
        """
        kwargs = {
            "url": url,
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "database": database,
            "enable_ssl": enable_ssl,
            "ensure_db": ensure_db,
            "debug": debug,
            **kwargs,
        }
        return _AsyncClientContext(cls, kwargs)

    @classmethod
    async def connect_async(
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
    ) -> "AsyncTiDBClient":
        """Create an async connection to TiDB.

        This method runs TiDBClient.connect() in a thread pool to avoid
        blocking the event loop during connection establishment.

        Use this method when you need to create a client directly without
        using a context manager. Remember to call disconnect() when done.

        Args:
            url: Connection URL. If None, constructed from other parameters.
            host: Database host (default: localhost).
            port: Database port (default: 4000).
            username: Database username (default: root).
            password: Database password (default: empty).
            database: Database name (default: test).
            enable_ssl: Enable SSL connection.
            ensure_db: Create database if it doesn't exist.
            debug: Enable debug mode.
            **kwargs: Additional arguments passed to SQLAlchemy create_engine().

        Returns:
            AsyncTiDBClient instance ready for async operations.

        Example:
            client = await AsyncTiDBClient.connect_async(
                host="localhost",
                port=4000,
                username="root",
                password="",
                database="mydb"
            )
            try:
                result = await client.query("SELECT * FROM users")
            finally:
                await client.disconnect()
        """
        sync_client = await asyncio.to_thread(
            TiDBClient.connect,
            url=url,
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
            enable_ssl=enable_ssl,
            ensure_db=ensure_db,
            debug=debug,
            **kwargs,
        )
        return cls(sync_client)

    async def disconnect(self) -> None:
        """Disconnect from the database.

        This method runs sync client's disconnect() in a thread pool.
        It's safe to call multiple times.

        Example:
            client = await AsyncTiDBClient.connect(...)
            await client.disconnect()
        """
        await asyncio.to_thread(self._sync_client.disconnect)

    async def __aenter__(self):
        """Async context manager entry.

        Returns:
            self: The AsyncTiDBClient instance.
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit.

        Automatically disconnects from the database when exiting the context.
        Connection is closed even if an exception occurs.

        Args:
            exc_type: Exception type if an exception occurred.
            exc_val: Exception value if an exception occurred.
            exc_tb: Exception traceback if an exception occurred.
        """
        await self.disconnect()

    # Database Management API

    async def create_database(
        self,
        name: str,
        if_exists: Optional[Literal["raise", "skip"]] = "raise",
    ) -> None:
        """Create a database asynchronously.

        Args:
            name: Name of the database to create.
            if_exists: Behavior if database already exists.
                      "raise" (default) raises an error.
                      "skip" silently skips.

        Example:
            await client.create_database("new_db")
        """
        await asyncio.to_thread(
            self._sync_client.create_database, name, if_exists=if_exists
        )

    async def drop_database(self, name: str) -> None:
        """Drop a database asynchronously.

        Args:
            name: Name of the database to drop.

        Example:
            await client.drop_database("old_db")
        """
        await asyncio.to_thread(self._sync_client.drop_database, name)

    async def list_databases(self) -> List[str]:
        """List all databases asynchronously.

        Returns:
            List of database names.

        Example:
            databases = await client.list_databases()
        """
        return await asyncio.to_thread(self._sync_client.list_databases)

    async def has_database(self, name: str) -> bool:
        """Check if a database exists asynchronously.

        Args:
            name: Database name to check.

        Returns:
            True if database exists, False otherwise.

        Example:
            if await client.has_database("mydb"):
                print("Database exists")
        """
        return await asyncio.to_thread(self._sync_client.has_database, name)

    async def current_database(self) -> Optional[str]:
        """Get the current database name asynchronously.

        Returns:
            Current database name or None if no database selected.

        Example:
            db = await client.current_database()
        """
        return await asyncio.to_thread(self._sync_client.current_database)

    async def use_database(self, database: str, *, ensure_db: Optional[bool] = False) -> None:
        """Switch to a different database asynchronously.

        Warning: Existing sessions will be destroyed.

        Args:
            database: Name of the database to switch to.
            ensure_db: If True, create database if it doesn't exist.

        Raises:
            ValueError: If database doesn't exist and ensure_db is False.

        Example:
            await client.use_database("new_db", ensure_db=True)
        """
        await asyncio.to_thread(
            self._sync_client.use_database, database, ensure_db=ensure_db
        )

    # Table Management API

    async def list_tables(self) -> List[str]:
        """List all tables in the current database asynchronously.

        Returns:
            List of table names.

        Example:
            tables = await client.list_tables()
        """
        return await asyncio.to_thread(self._sync_client.list_tables)

    async def has_table(self, table_name: str) -> bool:
        """Check if a table exists asynchronously.

        Args:
            table_name: Table name to check.

        Returns:
            True if table exists, False otherwise.

        Example:
            if await client.has_table("users"):
                print("Table exists")
        """
        return await asyncio.to_thread(self._sync_client.has_table, table_name)

    async def create_table(
        self,
        *,
        schema: Optional[Type[TableModel]] = None,
        if_exists: Optional[Literal["raise", "overwrite", "skip"]] = "raise",
    ) -> Table:
        """Create a table asynchronously.

        Args:
            schema: TableModel schema defining the table structure.
            if_exists: Behavior if table already exists.
                      "raise" (default) raises an error.
                      "overwrite" drops and recreates the table.
                      "skip" silently skips.

        Returns:
            Table instance for the created table.

        Example:
            from pytidb.schema import TableModel, Field

            class User(TableModel):
                __tablename__ = "users"
                id: int = Field(primary_key=True)
                name: str

            table = await client.create_table(schema=User)
        """
        return await asyncio.to_thread(
            self._sync_client.create_table, schema=schema, if_exists=if_exists
        )

    async def drop_table(
        self,
        table_name: str,
        if_not_exists: Optional[Literal["raise", "skip"]] = "raise",
    ) -> None:
        """Drop a table asynchronously.

        Args:
            table_name: Name of the table to drop.
            if_not_exists: Behavior if table doesn't exist.
                          "raise" (default) raises an error.
                          "skip" silently skips.

        Example:
            await client.drop_table("old_table")
        """
        await asyncio.to_thread(
            self._sync_client.drop_table, table_name, if_not_exists=if_not_exists
        )

    # Raw SQL API

    async def execute(
        self,
        sql: str | Executable,
        params: Optional[dict] = None,
        raise_error: Optional[bool] = False,
    ) -> SQLExecuteResult:
        """Execute SQL asynchronously.

        Args:
            sql: SQL string or SQLAlchemy Executable to execute.
            params: Optional parameters for the SQL query.
            raise_error: If True, raise exception on error instead
                        of returning SQLExecuteResult with success=False.

        Returns:
            SQLExecuteResult with rowcount, success status, and message.

        Example:
            result = await client.execute(
                "INSERT INTO users VALUES (:id, :name)",
                params={"id": 1, "name": "Alice"}
            )
            if result.success:
                print(f"Inserted {result.rowcount} rows")
        """
        return await asyncio.to_thread(
            self._sync_client.execute, sql, params=params, raise_error=raise_error
        )

    async def query(
        self,
        sql: str | SelectBase,
        params: Optional[dict] = None,
    ) -> "AsyncSQLQueryResult":
        """Execute a query asynchronously.

        This method executes the query in a thread pool and immediately materializes
        all results before returning. This ensures thread safety by avoiding the need
        to access SQLAlchemy Result objects across different threads.

        Args:
            sql: SQL string or SQLAlchemy SelectBase to query.
            params: Optional parameters for the SQL query.

        Returns:
            AsyncSQLQueryResult with materialized data ready for async consumption.

        Example:
            result = await client.query("SELECT * FROM users WHERE id = :id", params={"id": 1})
            users = await result.to_list()
            for user in users:
                print(user)
        """
        def _run_and_materialize():
            sync_result = self._sync_client.query(sql, params=params)
            # Materialize all data in the same thread where the query executed
            # First get scalar value before draining the result with to_list()
            scalar_val = sync_result.scalar()
            rows = sync_result.to_list()
            return rows, scalar_val

        rows, scalar_val = await asyncio.to_thread(_run_and_materialize)
        return AsyncSQLQueryResult(rows=rows, scalar_val=scalar_val)

    async def configure_embedding_provider(
        self, provider: str, api_key: str
    ) -> SQLExecuteResult:
        """Configure embedding provider asynchronously.

        Args:
            provider: Name of the embedding provider (e.g., "openai").
            api_key: API key for the provider.

        Returns:
            SQLExecuteResult with success status.

        Example:
            result = await client.configure_embedding_provider("openai", api_key="sk-...")
        """
        return await asyncio.to_thread(
            self._sync_client.configure_embedding_provider, provider, api_key
        )
