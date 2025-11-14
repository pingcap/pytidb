"""
Async table operations for PyTiDB.

This module provides async versions of table operations while maintaining
backward compatibility with the synchronous API.
"""
import asyncio
from typing import Optional, List, Dict, Any, Union, TypeVar, Type

from pytidb.table import Table
from pytidb.schema import TableModel
from pytidb.result import QueryResult, SQLModelQueryResult, SQLQueryResult
from pytidb.async_result import AsyncQueryResult, AsyncSQLQueryResult

# Type variable for table models
T = TypeVar("T", bound=TableModel)


class AsyncTable:
    """
    Async wrapper for Table operations.

    This class provides async versions of all Table operations by running
    the synchronous operations in a thread pool using asyncio.to_thread().

    Example:
        >>> async with AsyncTiDBClient.connect(**params) as client:
        ...     table = await client.get_table("users")
        ...     result = await table.insert({"name": "John", "age": 25})
        ...     users = await table.select(filters={"age": {"$gt": 18}})
    """

    def __init__(self, sync_table: Table):
        """
        Initialize the async table wrapper.

        Args:
            sync_table: The synchronous Table instance to wrap
        """
        self._sync_table = sync_table

    @property
    def name(self) -> str:
        """Get the table name."""
        return self._sync_table.name

    @property
    def model(self) -> Optional[Type[TableModel]]:
        """Get the table model class."""
        return getattr(self._sync_table, 'model', None)

    async def insert(self, data: Union[T, Dict[str, Any]]) -> T:
        """
        Insert data into the table asynchronously.

        Args:
            data: Dictionary or model instance to insert

        Returns:
            The inserted model instance

        Example:
            >>> # Insert dictionary
            >>> result = await table.insert({"name": "John", "age": 25})

            >>> # Insert model instance
            >>> user = User(name="Jane", age=30)
            >>> result = await table.insert(user)
        """
        return await asyncio.to_thread(self._sync_table.insert, data)

    async def select(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        order_by: Optional[List[str]] = None,
        **kwargs
    ) -> AsyncSQLQueryResult:
        """
        Select data from the table asynchronously.

        Args:
            filters: Optional filters to apply
            limit: Optional limit on number of results
            order_by: Optional ordering specification
            **kwargs: Additional query parameters

        Returns:
            AsyncSQLQueryResult containing the selected data

        Example:
            >>> # Select all
            >>> result = await table.select()
            >>> users = await result.to_list()

            >>> # Select with filters
            >>> result = await table.select(filters={"age": {"$gt": 18}})
            >>> adults = await result.to_list()

            >>> # Select with limit and ordering
            >>> result = await table.select(limit=10, order_by=["age DESC"])
            >>> top_10 = await result.to_list()
        """
        # Call the sync method and wrap the result
        sync_result = await asyncio.to_thread(
            self._sync_table.select,
            filters=filters,
            limit=limit,
            order_by=order_by,
            **kwargs
        )
        return AsyncSQLQueryResult(sync_result)

    async def update(
        self,
        values: Dict[str, Any],
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Update data in the table asynchronously.

        Args:
            values: Dictionary of values to update
            filters: Optional filters to determine which rows to update
            **kwargs: Additional update parameters

        Returns:
            Update operation result

        Example:
            >>> # Update all rows
            >>> await table.update({"status": "active"})

            >>> # Update with filters
            >>> await table.update({"status": "inactive"}, filters={"last_login": {"$lt": "2024-01-01"}})
        """
        return await asyncio.to_thread(
            self._sync_table.update,
            values=values,
            filters=filters,
            **kwargs
        )

    async def delete(
        self,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Delete data from the table asynchronously.

        Args:
            filters: Optional filters to determine which rows to delete
            **kwargs: Additional delete parameters

        Returns:
            Delete operation result

        Example:
            >>> # Delete all rows
            >>> await table.delete()

            >>> # Delete with filters
            >>> await table.delete(filters={"status": "inactive"})
        """
        return await asyncio.to_thread(
            self._sync_table.delete,
            filters=filters,
            **kwargs
        )

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        search_type: Optional[str] = None,
        **kwargs
    ) -> AsyncSQLQueryResult:
        """
        Search the table asynchronously.

        Args:
            query: Search query string
            filters: Optional filters to apply alongside search
            search_type: Optional search type specification
            **kwargs: Additional search parameters

        Returns:
            AsyncSQLQueryResult containing search results

        Example:
            >>> # Simple search
            >>> result = await table.search("find active users")
            >>> users = await result.to_list()

            >>> # Search with filters
            >>> result = await table.search("users", filters={"age": {"$gt": 18}})
            >>> filtered_users = await result.to_list()
        """
        # Call the sync method and wrap the result
        sync_result = await asyncio.to_thread(
            self._sync_table.search,
            query=query,
            filters=filters,
            search_type=search_type,
            **kwargs
        )
        return AsyncSQLQueryResult(sync_result)

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count rows in the table asynchronously.

        Args:
            filters: Optional filters to apply when counting

        Returns:
            Number of rows matching the criteria

        Example:
            >>> # Count all rows
            >>> total = await table.count()

            >>> # Count with filters
            >>> active_count = await table.count(filters={"status": "active"})
        """
        return await asyncio.to_thread(self._sync_table.count, filters=filters)

    async def exists(self, filters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if rows exist in the table asynchronously.

        Args:
            filters: Optional filters to apply when checking existence

        Returns:
            True if matching rows exist, False otherwise

        Example:
            >>> # Check if any users exist
            >>> has_users = await table.exists()

            >>> # Check if active users exist
            >>> has_active = await table.exists(filters={"status": "active"})
        """
        return await asyncio.to_thread(self._sync_table.exists, filters=filters)

    async def create_index(
        self,
        column_name: str,
        index_type: str = "btree",
        **kwargs
    ) -> Any:
        """
        Create an index on the table asynchronously.

        Args:
            column_name: Name of the column to index
            index_type: Type of index (btree, hash, etc.)
            **kwargs: Additional index parameters

        Returns:
            Index creation result

        Example:
            >>> # Create btree index
            >>> await table.create_index("email")

            >>> # Create hash index
            >>> await table.create_index("username", index_type="hash")
        """
        return await asyncio.to_thread(
            self._sync_table.create_index,
            column_name=column_name,
            index_type=index_type,
            **kwargs
        )

    async def drop_index(self, index_name: str, **kwargs) -> Any:
        """
        Drop an index from the table asynchronously.

        Args:
            index_name: Name of the index to drop
            **kwargs: Additional drop parameters

        Returns:
            Index drop result

        Example:
            >>> await table.drop_index("idx_email")
        """
        return await asyncio.to_thread(
            self._sync_table.drop_index,
            index_name=index_name,
            **kwargs
        )

    async def truncate(self, **kwargs) -> Any:
        """
        Truncate the table asynchronously.

        Args:
            **kwargs: Additional truncate parameters

        Returns:
            Truncate operation result

        Example:
            >>> await table.truncate()
        """
        return await asyncio.to_thread(self._sync_table.truncate, **kwargs)

    def __repr__(self) -> str:
        """String representation of the async table."""
        return f"AsyncTable(name='{self.name}')"

    def __str__(self) -> str:
        """String representation of the async table."""
        return self.__repr__()