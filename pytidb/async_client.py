"""
Async client for PyTiDB.

This module provides an async wrapper around the synchronous TiDBClient,
allowing for asynchronous database operations while maintaining full
backward compatibility with the existing synchronous API.
"""
import asyncio
from typing import Optional, Dict, Any, List, Union, Generator
from contextlib import asynccontextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import Result
from sqlmodel import Session

from pytidb.client import TiDBClient
from pytidb.table import Table
from pytidb.async_table import AsyncTable
from pytidb.async_result import AsyncSQLQueryResult, AsyncSQLExecuteResult
from pytidb.async_session import AsyncSessionProxy
from pytidb.result import SQLQueryResult, SQLExecuteResult
from pytidb.utils import build_tidb_connection_url


class _ConnectContext:
    """
    Helper class to make AsyncTiDBClient.connect() work with async with.

    This class wraps the connection coroutine and makes it both awaitable
    and usable as an async context manager.
    """

    def __init__(self, connect_coro):
        """Initialize with the connection coroutine."""
        self._connect_coro = connect_coro
        self._client = None

    def __await__(self):
        """Make it awaitable."""
        return self._connect_coro.__await__()

    async def __aenter__(self):
        """Enter async context manager."""
        self._client = await self._connect_coro
        return self._client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager and disconnect."""
        if self._client:
            await self._client.disconnect()


class AsyncTiDBClient:
    """
    Async wrapper for TiDBClient.

    This class provides async versions of all TiDBClient operations by running
    the synchronous operations in a thread pool using asyncio.to_thread().

    Example:
        >>> # Using async context manager with connect
        >>> async with AsyncTiDBClient.connect(**params) as client:
        ...     # Execute SQL queries
        ...     result = await client.execute_sql("SELECT * FROM users")
        ...     users = await result.to_list()
        ...
        ...     # Work with tables
        ...     table = await client.get_table("users")
        ...     await table.insert({"name": "John", "age": 25})
        ...     # Client is automatically disconnected on exit

        >>> # Using manual connection management
        >>> client = await AsyncTiDBClient.connect(**params)
        >>> try:
        ...     result = await client.execute_sql("SELECT COUNT(*) FROM users")
        ...     count = await result.scalar()
        ... finally:
        ...     await client.disconnect()
    """

    def __init__(self, sync_client: TiDBClient):
        """
        Initialize the async client wrapper.

        Args:
            sync_client: The synchronous TiDBClient instance to wrap
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
        **kwargs
    ) -> _ConnectContext:
        """
        Connect to TiDB asynchronously.

        This method creates a new async TiDB client connection by wrapping
        the synchronous TiDBClient.connect() method.

        Args:
            url: Connection URL (optional, will be built from other params if not provided)
            host: Database host
            port: Database port
            username: Database username
            password: Database password
            database: Database name
            enable_ssl: Whether to enable SSL
            ensure_db: Whether to ensure database exists
            debug: Whether to enable debug mode
            **kwargs: Additional connection parameters

        Returns:
            _ConnectContext that is both awaitable and an async context manager

        Example:
            >>> # Using with async with (client automatically disconnected)
            >>> async with AsyncTiDBClient.connect(
            ...     host="localhost",
            ...     port=4000,
            ...     username="root",
            ...     password="password",
            ...     database="myapp"
            ... ) as client:
            ...     result = await client.execute_sql("SELECT * FROM users")
            ...     users = await result.to_list()

            >>> # Using with await (manual disconnect required)
            >>> client = await AsyncTiDBClient.connect(
            ...     url="mysql://root:password@localhost:4000/myapp"
            ... )
            >>> try:
            ...     result = await client.execute_sql("SELECT * FROM users")
            ... finally:
            ...     await client.disconnect()
        """

        async def _do_connect():
            """Helper function to perform the actual connection."""
            # Run the synchronous connect method in a thread pool
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
                **kwargs
            )
            return cls(sync_client)

        # Return a context that is both awaitable and an async context manager
        return _ConnectContext(_do_connect())

    async def disconnect(self) -> None:
        """
        Disconnect from TiDB asynchronously.

        This method closes the database connection and cleans up resources.

        Example:
            >>> client = await AsyncTiDBClient.connect(**params)
            >>> try:
            ...     # Use client
            ... finally:
            ...     await client.disconnect()
        """
        await asyncio.to_thread(self._sync_client.disconnect)

    async def execute_sql(self, sql: str, params: Optional[List[Any]] = None) -> AsyncSQLQueryResult:
        """
        Execute a SQL query asynchronously and return results.

        This method wraps the underlying synchronous `query()` method,
        which executes SELECT statements and returns query results.
        For INSERT, UPDATE, DELETE operations, use `execute()` instead.

        Args:
            sql: SQL query string (SELECT statements)
            params: Optional list of parameters for the query

        Returns:
            AsyncSQLQueryResult containing query results

        Example:
            >>> # Simple query
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> users = await result.to_list()

            >>> # Parameterized query
            >>> result = await client.execute_sql(
            ...     "SELECT * FROM users WHERE age > ?",
            ...     params=[18]
            ... )
            >>> adults = await result.to_list()
        """
        # Execute the SQL using the sync client's query method
        # which properly handles SELECT statements
        sync_result = await asyncio.to_thread(
            self._sync_client.query,
            sql,
            params=params
        )

        # Wrap the result in an async wrapper
        return AsyncSQLQueryResult(sync_result)

    async def execute(self, sql: str, params: Optional[List[Any]] = None) -> AsyncSQLExecuteResult:
        """
        Execute a SQL statement asynchronously (INSERT, UPDATE, DELETE, etc.).

        Args:
            sql: SQL statement string
            params: Optional list of parameters for the statement

        Returns:
            AsyncSQLExecuteResult containing execution results

        Example:
            >>> # Insert statement
            >>> result = await client.execute(
            ...     "INSERT INTO users (name, age) VALUES (?, ?)",
            ...     params=["John", 25]
            ... )
            >>> affected_rows = await result.rowcount()

            >>> # Update statement
            >>> result = await client.execute(
            ...     "UPDATE users SET status = ? WHERE age > ?",
            ...     params=["active", 18]
            ... )
            >>> affected_rows = await result.rowcount()
        """
        # Execute the SQL and get the synchronous result
        sync_result = await asyncio.to_thread(
            self._sync_client.execute,
            sql,
            params=params
        )

        # Wrap the result in an async wrapper
        return AsyncSQLExecuteResult(sync_result)

    async def get_table(self, table_name: str) -> AsyncTable:
        """
        Get a table by name asynchronously.

        This method wraps the synchronous `open_table()` method to retrieve
        a table from the database.

        Args:
            table_name: Name of the table

        Returns:
            AsyncTable instance for the specified table

        Example:
            >>> table = await client.get_table("users")
            >>> result = await table.select()
            >>> users = await result.to_list()
        """
        # Call the sync open_table method and wrap the result
        sync_table = await asyncio.to_thread(
            self._sync_client.open_table,
            table_name
        )

        # Wrap it in an async table
        return AsyncTable(sync_table)

    async def use_database(self, database: str) -> None:
        """
        Switch to a different database asynchronously.

        Args:
            database: Name of the database to switch to

        Example:
            >>> await client.use_database("new_database")
            >>> # Now all operations will use the new database
        """
        await asyncio.to_thread(self._sync_client.use_database, database)

    async def create_database(self, database: str) -> None:
        """
        Create a new database asynchronously.

        Args:
            database: Name of the database to create

        Example:
            >>> await client.create_database("my_new_database")
        """
        await asyncio.to_thread(self._sync_client.create_database, database)

    async def drop_database(self, database: str) -> None:
        """
        Drop a database asynchronously.

        Args:
            database: Name of the database to drop

        Example:
            >>> await client.drop_database("old_database")
        """
        await asyncio.to_thread(self._sync_client.drop_database, database)

    async def database_exists(self, database: str) -> bool:
        """
        Check if a database exists asynchronously.

        Args:
            database: Name of the database to check

        Returns:
            True if the database exists, False otherwise

        Example:
            >>> exists = await client.database_exists("my_database")
            >>> if exists:
            ...     print("Database exists")
        """
        return await asyncio.to_thread(self._sync_client.database_exists, database)

    async def list_databases(self) -> List[str]:
        """
        List all databases asynchronously.

        Returns:
            List of database names

        Example:
            >>> databases = await client.list_databases()
            >>> print(f"Available databases: {databases}")
        """
        return await asyncio.to_thread(self._sync_client.list_databases)

    async def list_tables(self) -> List[str]:
        """
        List all tables in the current database asynchronously.

        Returns:
            List of table names

        Example:
            >>> tables = await client.list_tables()
            >>> print(f"Available tables: {tables}")
        """
        return await asyncio.to_thread(self._sync_client.list_tables)

    @property
    def database(self) -> str:
        """
        Get the current database name.

        The database name is derived from the SQLAlchemy engine's URL.
        If the engine doesn't have a URL or the URL doesn't contain a database,
        an empty string is returned.

        Returns:
            str: The name of the currently connected database

        Example:
            >>> async with AsyncTiDBClient.connect(
            ...     database="myapp"
            ... ) as client:
            ...     print(client.database)  # Output: myapp
            myapp
        """
        try:
            engine = self._sync_client._db_engine
            if hasattr(engine, 'url') and hasattr(engine.url, 'database'):
                database = engine.url.database
                return database if database is not None else ""
            return ""
        except Exception:
            return ""

    @property
    def engine(self) -> Engine:
        """Get the SQLAlchemy engine."""
        return self._sync_client._db_engine

    async def __aenter__(self) -> "AsyncTiDBClient":
        """
        Async context manager entry.

        This method is called when entering an `async with` block.

        Returns:
            self: The AsyncTiDBClient instance

        Example:
            >>> async with AsyncTiDBClient.connect(**params) as client:
            ...     # Use client here
            ...     pass
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Async context manager exit.

        This method is called when exiting an `async with` block.
        It automatically disconnects the client.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Example:
            >>> async with AsyncTiDBClient.connect(**params) as client:
            ...     # Client is automatically disconnected when block exits
            ...     pass
        """
        await self.disconnect()

    def __repr__(self) -> str:
        """String representation of the async client."""
        return f"AsyncTiDBClient(database='{self.database}')"

    def __str__(self) -> str:
        """String representation of the async client."""
        return self.__repr__()

    @asynccontextmanager
    async def session(self):
        """
        Async context manager for database sessions with proper thread affinity.

        This provides a thread-safe way to work with SQLAlchemy sessions in an async context.
        The session is created and managed on a dedicated thread, ensuring all operations
        maintain proper thread affinity and transaction consistency.

        Proper exception propagation ensures that transactions are correctly
        committed or rolled back based on whether an exception occurred.

        All operations within the async context manager share the same session and transaction.

        Example:
            >>> async with client.session() as session:
            ...     # All operations share the same session and transaction
            ...     await session.execute("INSERT INTO users (name) VALUES ('John')")
            ...     await session.execute("INSERT INTO users (name) VALUES ('Jane')")
            ...     await session.commit()  # Both inserts in one transaction
            >>>
            >>> # Exception triggers rollback
            >>> async with client.session() as session:
            ...     await session.execute("INSERT INTO users (name) VALUES ('Bob')")
            ...     raise Exception("Force rollback")
            ...     await session.execute("INSERT INTO users (name) VALUES ('Alice')")
        """
        # Create session factory
        def session_factory():
            return self._sync_client._session()

        # Create async session proxy
        async with AsyncSessionProxy(session_factory) as session_proxy:
            yield session_proxy


# Convenience alias for backward compatibility and ease of use
AsyncConnection = AsyncTiDBClient