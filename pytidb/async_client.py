"""
Async wrapper for PyTiDB Client using asyncio.to_thread pattern.

This module provides async versions of TiDBClient and Table classes,
allowing non-blocking database operations in asyncio applications.
"""

import asyncio
from typing import Optional, Literal, List, Dict, Any, Type, Union, TYPE_CHECKING, Generic
from contextlib import asynccontextmanager

from sqlalchemy import create_engine  # Re-export for test patching
from sqlalchemy.exc import NoResultFound, MultipleResultsFound
from . import TiDBClient, Table
from .schema import TableModel
from .result import SQLExecuteResult, SQLQueryResult as _SQLQueryResult
from pydantic import BaseModel

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class AsyncTiDBClient:
    """
    Async wrapper for TiDBClient.

    Wraps all synchronous operations with asyncio.to_thread to provide
    non-blocking database operations.

    Example:
        async with AsyncTiDBClient.connect(host="localhost", port=4000) as client:
            result = await client.execute("INSERT INTO test VALUES (1)")
            query_result = await client.query("SELECT * FROM test")
    """

    def __init__(self, sync_client: TiDBClient):
        """
        Initialize AsyncTiDBClient with a sync TiDBClient instance.

        Args:
            sync_client: The synchronous TiDBClient instance to wrap.
        """
        self._sync_client = sync_client
        self._reconnect_params: Dict[str, Any] = sync_client._reconnect_params
        self._identifier_preparer = sync_client._identifier_preparer

    # Class method factories

    @classmethod
    async def connect(
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
        """
        Create an async TiDB client connection.

        Args:
            url: Database connection URL. If not provided, constructed from other args.
            host: Database host. Defaults to "localhost".
            port: Database port. Defaults to 4000.
            username: Database username. Defaults to "root".
            password: Database password. Defaults to "".
            database: Database name. Defaults to "test".
            enable_ssl: Whether to enable SSL.
            ensure_db: If True, create database if it doesn't exist.
            debug: Enable debug mode.
            **kwargs: Additional arguments passed to create_engine.

        Returns:
            AsyncTiDBClient instance.

        Example:
            client = await AsyncTiDBClient.connect(
                host="localhost",
                port=4000,
                username="root",
                database="mydb"
            )
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

    # Context manager support

    def __enter__(self):
        raise TypeError(
            "Use 'async with' instead of 'with' for AsyncTiDBClient"
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    async def __aenter__(self) -> "AsyncTiDBClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - disconnect from database."""
        await self.disconnect()

    @property
    def db_engine(self) -> "Engine":
        """Get the database engine from the sync client."""
        return self._sync_client.db_engine

    @property
    def is_serverless(self) -> bool:
        """Check if connected to TiDB Serverless."""
        return self._sync_client.is_serverless

    # Database management

    async def create_database(
        self,
        name: str,
        if_exists: Optional[Literal["raise", "skip"]] = "raise",
    ) -> Any:
        """
        Create a database.

        Args:
            name: Database name.
            if_exists: Action if database exists ("raise" or "skip").

        Returns:
            Result of the create operation.
        """
        sync_method = self._sync_client.create_database
        return await asyncio.to_thread(sync_method, name, if_exists=if_exists)

    async def drop_database(self, name: str) -> Any:
        """
        Drop a database.

        Args:
            name: Database name.

        Returns:
            Result of the drop operation.
        """
        sync_method = self._sync_client.drop_database
        return await asyncio.to_thread(sync_method, name)

    async def list_databases(self) -> List[str]:
        """
        List all databases.

        Returns:
            List of database names.
        """
        sync_method = self._sync_client.list_databases
        return await asyncio.to_thread(sync_method)

    async def has_database(self, name: str) -> bool:
        """
        Check if database exists.

        Args:
            name: Database name.

        Returns:
            True if database exists, False otherwise.
        """
        sync_method = self._sync_client.has_database
        return await asyncio.to_thread(sync_method, name)

    async def current_database(self) -> Optional[str]:
        """
        Get current database name.

        Returns:
            Current database name or None.
        """
        sync_method = self._sync_client.current_database
        return await asyncio.to_thread(sync_method)

    async def use_database(
        self, database: str, *, ensure_db: Optional[bool] = False
    ) -> None:
        """
        Switch to a different database.

        Args:
            database: Database name.
            ensure_db: If True, create database if it doesn't exist.
        """
        sync_method = self._sync_client.use_database
        await asyncio.to_thread(sync_method, database, ensure_db=ensure_db)

    # Table management

    async def create_table(
        self,
        *,
        schema: Optional[Type[TableModel]] = None,
        if_exists: Optional[Literal["raise", "overwrite", "skip"]] = "raise",
    ) -> "AsyncTable":
        """
        Create a table.

        Args:
            schema: Table schema.
            if_exists: Action if table exists ("raise", "overwrite", or "skip").

        Returns:
            AsyncTable instance.
        """
        sync_method = self._sync_client.create_table
        sync_table = await asyncio.to_thread(
            sync_method, schema=schema, if_exists=if_exists
        )
        return AsyncTable(sync_table=sync_table)

    async def open_table(self, table_name: str) -> Optional["AsyncTable"]:
        """
        Open an existing table.

        Args:
            table_name: Name of the table.

        Returns:
            AsyncTable instance or None if not found.
        """
        sync_method = self._sync_client.open_table
        sync_table = await asyncio.to_thread(sync_method, table_name)
        if sync_table is None:
            return None
        return AsyncTable(sync_table=sync_table)

    async def list_tables(self) -> List[str]:
        """
        List all tables in current database.

        Returns:
            List of table names.
        """
        sync_method = self._sync_client.list_tables
        return await asyncio.to_thread(sync_method)

    async def has_table(self, table_name: str) -> bool:
        """
        Check if table exists.

        Args:
            table_name: Table name.

        Returns:
            True if table exists, False otherwise.
        """
        sync_method = self._sync_client.has_table
        return await asyncio.to_thread(sync_method, table_name)

    async def drop_table(
        self,
        table_name: str,
        if_not_exists: Optional[Literal["raise", "skip"]] = "raise",
    ) -> None:
        """
        Drop a table.

        Args:
            table_name: Table name.
            if_not_exists: Action if table doesn't exist ("raise" or "skip").
        """
        sync_method = self._sync_client.drop_table
        await asyncio.to_thread(sync_method, table_name, if_not_exists=if_not_exists)

    # Raw SQL API

    async def execute(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        raise_error: Optional[bool] = False,
    ) -> SQLExecuteResult:
        """
        Execute a SQL statement.

        Args:
            sql: SQL statement to execute.
            params: Parameters for the SQL statement.
            raise_error: If True, raise exceptions instead of returning error result.

        Returns:
            SQLExecuteResult with operation result.

        Example:
            result = await client.execute(
                "INSERT INTO users (name) VALUES (:name)",
                {"name": "Alice"}
            )
        """
        sync_method = self._sync_client.execute
        return await asyncio.to_thread(
            sync_method, sql, params=params, raise_error=raise_error
        )

    async def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> "AsyncQueryResult":
        """
        Execute a SQL query and return results.

        Args:
            sql: SQL query to execute.
            params: Parameters for the SQL query.

        Returns:
            AsyncQueryResult with materialized data.
        """
        def _materialize_query():
            # Execute query and materialize all data within the worker thread
            sync_result = self._sync_client.query(sql, params=params)

            # Materialize all data before returning - this avoids cross-thread cursor access
            keys = list(sync_result._result.keys())
            rows = sync_result._result.fetchall()

            return AsyncQueryResult(keys, rows)

        return await asyncio.to_thread(_materialize_query)

    async def configure_embedding_provider(
        self, provider: str, api_key: str
    ) -> SQLExecuteResult:
        """
        Configure embedding provider API key.

        Args:
            provider: Provider name (e.g., "openai").
            api_key: API key for the provider.

        Returns:
            SQLExecuteResult with configuration result.
        """
        sync_method = self._sync_client.configure_embedding_provider
        return await asyncio.to_thread(sync_method, provider, api_key)

    # Connection management

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        sync_method = self._sync_client.disconnect
        await asyncio.to_thread(sync_method)


class AsyncQueryResult:
    """
    Async-friendly wrapper for query results that materializes data within the worker thread.

    This prevents cross-thread cursor access which violates DBAPI thread-safety.
    All data is fetched within the worker thread, and this class provides synchronous accessors
    to the already-materialized data, maintaining API parity with the sync version.
    """

    def __init__(self, keys, rows, rowcount=None):
        """
        Initialize with materialized data.

        Args:
            keys: Column names
            rows: List of row tuples
            rowcount: Number of rows affected (for execute operations)
        """
        self._keys = keys
        self._rows = rows
        self._rowcount = rowcount
        self._data = [dict(zip(keys, row)) for row in rows] if keys and rows else []

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert results to list of dictionaries."""
        return self._data

    def scalar(self):
        """Get single scalar value."""
        if not self._rows:
            return None
        return self._rows[0][0] if self._rows[0] else None

    def one(self):
        """
        Return exactly one result or raise an exception.

        Raises:
            NoResultFound: If no results are found
            MultipleResultsFound: If multiple results are found

        Returns:
            Dictionary representing the single result row
        """
        if len(self._data) == 0:
            raise NoResultFound("No row was found when one was required")
        elif len(self._data) > 1:
            raise MultipleResultsFound(
                "Multiple rows were found when exactly one was required"
            )
        return self._data[0]

    def to_rows(self):
        """Get results as list of tuples."""
        return self._rows

    def to_pandas(self):
        """Convert results to pandas DataFrame."""
        try:
            import pandas as pd
        except ImportError as e:
            raise ImportError("Failed to import pandas, please install with `pip install pandas`") from e
        return pd.DataFrame(self._rows, columns=self._keys)

    def to_pydantic(self, model: Type[BaseModel]) -> List[BaseModel]:
        """Convert results to pydantic model instances."""
        return [model.model_validate(item) for item in self._data]


class AsyncTable:
    """
    Async wrapper for Table.

    Provides async versions of all table operations.
    """

    def __init__(
        self,
        sync_table: Optional[Table] = None,
        *,
        client: Optional["AsyncTiDBClient"] = None,
        schema: Optional[Type[TableModel]] = None,
    ):
        """
        Initialize AsyncTable.

        Can be initialized in two ways:
        1. With a sync_table: AsyncTable(sync_table=table)
        2. With schema and client: AsyncTable(client=async_client, schema=UserSchema)

        Args:
            sync_table: Existing synchronous Table instance to wrap (internal use).
            client: AsyncTiDBClient instance (public API, matches sync Table).
            schema: Table schema (public API, matches sync Table).

        Raises:
            ValueError: If neither sync_table nor (client and schema) are provided.
            TypeError: If client is not an AsyncTiDBClient instance.
        """
        if sync_table is not None:
            # Initialize from existing sync table (internal wrapping)
            self._sync_table = sync_table
            self._table_model = sync_table.table_model
            self._table_name = sync_table.table_name
        elif client is not None and schema is not None:
            # Initialize from schema and client (public API, matches sync Table)
            if not isinstance(client, AsyncTiDBClient):
                raise TypeError(
                    f"client must be an AsyncTiDBClient instance, got {type(client)}"
                )
            # Create sync table from the sync client
            sync_client = client._sync_client
            self._sync_table = Table(schema=schema, client=sync_client)
            self._table_model = self._sync_table.table_model
            self._table_name = self._sync_table.table_name
        else:
            raise ValueError(
                "AsyncTable must be initialized with either sync_table or "
                "both client and schema parameters"
            )

    @property
    def table_model(self):
        """Get the table model."""
        return self._table_model

    @property
    def table_name(self) -> str:
        """Get the table name."""
        return self._table_name

    # CRUD operations

    async def insert(self, data) -> Any:
        """
        Insert a single record.

        Args:
            data: Record data as dict or model instance.

        Returns:
            Inserted record.
        """
        sync_method = self._sync_table.insert
        return await asyncio.to_thread(sync_method, data)

    async def bulk_insert(self, data: list) -> list:
        """
        Insert multiple records.

        Args:
            data: List of records to insert.

        Returns:
            List of inserted records.
        """
        sync_method = self._sync_table.bulk_insert
        return await asyncio.to_thread(sync_method, data)

    async def update(self, values: Dict[str, Any], filters=None) -> None:
        """
        Update records.

        Args:
            values: Values to update.
            filters: Filter conditions.
        """
        sync_method = self._sync_table.update
        await asyncio.to_thread(sync_method, values, filters)

    async def delete(self, filters=None) -> None:
        """
        Delete records.

        Args:
            filters: Filter conditions.
        """
        sync_method = self._sync_table.delete
        await asyncio.to_thread(sync_method, filters)

    async def get(self, id: Any) -> Optional[Any]:
        """
        Get a record by ID.

        Args:
            id: Record ID.

        Returns:
            Record or None if not found.
        """
        sync_method = self._sync_table.get
        return await asyncio.to_thread(sync_method, id)

    async def query(self, filters=None, order_by=None, limit=None, offset=None):
        """
        Query records with filters.

        Args:
            filters: Filter conditions.
            order_by: Ordering specification.
            limit: Limit number of results.
            offset: Skip number of results.

        Returns:
            Query result.
        """
        sync_method = self._sync_table.query
        return await asyncio.to_thread(
            sync_method,
            filters=filters,
            order_by=order_by,
            limit=limit,
            offset=offset,
        )

    # Table management

    async def create(self, if_exists: Literal["raise", "skip"] = "raise"):
        """
        Create the table.

        Args:
            if_exists: Action if table exists ("raise" or "skip").

        Returns:
            AsyncTable instance.
        """
        sync_method = self._sync_table.create
        await asyncio.to_thread(sync_method, if_exists=if_exists)
        return self

    async def drop(self, if_not_exists: Literal["raise", "skip"] = "raise") -> None:
        """
        Drop the table.

        Args:
            if_not_exists: Action if table doesn't exist ("raise" or "skip").
        """
        sync_method = self._sync_table.drop
        await asyncio.to_thread(sync_method, if_not_exists=if_not_exists)

    async def truncate(self) -> None:
        """Truncate all records from the table."""
        sync_method = self._sync_table.truncate
        await asyncio.to_thread(sync_method)

    # Analytics

    async def rows(self) -> int:
        """
        Count rows in the table.

        Returns:
            Number of rows.
        """
        sync_method = self._sync_table.rows
        return await asyncio.to_thread(sync_method)

    async def columns(self) -> list:
        """
        Get column information.

        Returns:
            List of column information.
        """
        sync_method = self._sync_table.columns
        return await asyncio.to_thread(sync_method)

    # Search

    async def search(self, query, search_type: str = "vector"):
        """
        Search the table.

        Args:
            query: Search query.
            search_type: Type of search ("vector", "fulltext", "hybrid").

        Returns:
            Search result.
        """
        sync_method = self._sync_table.search
        return await asyncio.to_thread(sync_method, query, search_type)
