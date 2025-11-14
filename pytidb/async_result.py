"""
Async result wrappers for PyTiDB.

This module provides async versions of the result classes to work with
the async API while maintaining backward compatibility with the sync API.
"""
import asyncio
from typing import List, Optional, Type, Any
from abc import ABC, abstractmethod

from sqlalchemy import Result
from pydantic import BaseModel

from pytidb.result import SQLQueryResult, QueryResult


class AsyncQueryResult(ABC):
    """Abstract base class for async query results."""

    @abstractmethod
    async def to_list(self) -> List[dict]:
        """Convert result to list of dictionaries asynchronously."""
        pass

    @abstractmethod
    async def to_pydantic(self, model: Type[BaseModel]) -> List[BaseModel]:
        """Convert result to list of Pydantic models asynchronously."""
        pass

    @abstractmethod
    async def to_pandas(self):
        """Convert result to pandas DataFrame asynchronously."""
        pass


class AsyncSQLQueryResult(AsyncQueryResult):
    """
    Async wrapper for SQLQueryResult.

    This class provides async versions of all SQLQueryResult methods
    by running the synchronous operations in a thread pool.
    """

    def __init__(self, sync_result: SQLQueryResult):
        """
        Initialize the async result wrapper.

        Args:
            sync_result: The synchronous SQLQueryResult to wrap
        """
        self._sync_result = sync_result

    async def scalar(self) -> Any:
        """
        Fetch the first column of the first row asynchronously.

        Returns:
            The scalar value, or None if no result

        Example:
            >>> result = await client.execute_sql("SELECT COUNT(*) FROM users")
            >>> count = await result.scalar()
        """
        return await asyncio.to_thread(self._sync_result.scalar)

    async def one(self) -> Any:
        """
        Fetch exactly one row asynchronously.

        Returns:
            The single row result

        Raises:
            NoResultFound: If no result is found
            MultipleResultsFound: If multiple results are found

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users WHERE id = 1")
            >>> user = await result.one()
        """
        return await asyncio.to_thread(self._sync_result.one)

    async def fetchall(self) -> List[tuple]:
        """
        Fetch all rows as a list of tuples asynchronously.

        Returns:
            List of tuples containing row data

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> rows = await result.fetchall()
        """
        return await asyncio.to_thread(self._sync_result.to_rows)

    async def to_list(self) -> List[dict]:
        """
        Convert result to list of dictionaries asynchronously.

        Returns:
            List of dictionaries with column names as keys

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> users = await result.to_list()
        """
        return await asyncio.to_thread(self._sync_result.to_list)

    async def to_pydantic(self, model: Type[BaseModel]) -> List[BaseModel]:
        """
        Convert result to list of Pydantic models asynchronously.

        Args:
            model: The Pydantic model class to convert to

        Returns:
            List of Pydantic model instances

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> users = await result.to_pydantic(UserModel)
        """
        return await asyncio.to_thread(self._sync_result.to_pydantic, model)

    async def to_pandas(self):
        """
        Convert result to pandas DataFrame asynchronously.

        Returns:
            pandas DataFrame containing the query results

        Raises:
            ImportError: If pandas is not installed

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> df = await result.to_pandas()
        """
        return await asyncio.to_thread(self._sync_result.to_pandas)

    async def keys(self) -> List[str]:
        """
        Get column names asynchronously.

        Returns:
            List of column names

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> columns = await result.keys()
        """
        return await asyncio.to_thread(self._sync_result._result.keys)

    async def first(self) -> Optional[dict]:
        """
        Fetch the first row as a dictionary asynchronously.

        Returns:
            First row as dictionary, or None if no results

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> first_user = await result.first()
        """
        rows = await self.to_list()
        return rows[0] if rows else None

    async def count(self) -> int:
        """
        Get the number of rows in the result asynchronously.

        Returns:
            Number of rows

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> user_count = await result.count()
        """
        rows = await self.fetchall()
        return len(rows)

    def __aiter__(self):
        """
        Make the result async iterable.

        Example:
            >>> result = await client.execute_sql("SELECT * FROM users")
            >>> async for row in result:
            ...     print(row)
        """
        return self._async_iterator()

    async def _async_iterator(self):
        """Async iterator implementation."""
        rows = await self.fetchall()
        keys = await self.keys()

        for row in rows:
            yield dict(zip(keys, row))


class AsyncSQLExecuteResult:
    """
    Async wrapper for SQL execution results.

    This class provides async access to SQL execution results
    such as INSERT, UPDATE, DELETE operations.
    """

    def __init__(self, sync_result):
        """
        Initialize the async execute result wrapper.

        Args:
            sync_result: The synchronous SQLExecuteResult
        """
        self._sync_result = sync_result

    async def rowcount(self) -> int:
        """
        Get the number of affected rows asynchronously.

        Returns:
            Number of rows affected by the operation

        Example:
            >>> result = await client.execute("UPDATE users SET status = 'active'")
            >>> affected_rows = await result.rowcount()
        """
        return await asyncio.to_thread(lambda: self._sync_result.rowcount)

    async def success(self) -> bool:
        """
        Check if the operation was successful asynchronously.

        Returns:
            True if the operation succeeded, False otherwise

        Example:
            >>> result = await client.execute("INSERT INTO users (name) VALUES ('John')")
            >>> if await result.success():
            ...     print("Insert successful")
        """
        return await asyncio.to_thread(lambda: self._sync_result.success)

    async def message(self) -> Optional[str]:
        """
        Get the operation message asynchronously.

        Returns:
            Operation message if available, None otherwise

        Example:
            >>> result = await client.execute("CREATE TABLE users (id INT)")
            >>> message = await result.message()
        """
        return await asyncio.to_thread(lambda: self._sync_result.message)

    def __repr__(self) -> str:
        """String representation of the async execute result."""
        return f"AsyncSQLExecuteResult(rowcount={getattr(self._sync_result, 'rowcount', 'unknown')}, success={getattr(self._sync_result, 'success', 'unknown')})"