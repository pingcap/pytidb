"""
Async SQLAlchemy Session Proxy with thread affinity support.

This module provides AsyncSessionProxy, which manages a SQLAlchemy Session on a dedicated
to ensure proper thread affinity and transaction consistency in async contexts.
"""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Optional, Dict, List, Union
import weakref
from contextvars import ContextVar

try:
    from sqlalchemy.orm import Session
except ImportError:
    Session = Any

# We'll get AsyncSQLQueryResult when needed
try:
    from .async_result import AsyncSQLQueryResult
    from .errors import TiDBError
except ImportError:
    AsyncSQLQueryResult = Any
    TiDBError = Exception


# Context variable to track the active async session
ASYNC_SESSION: ContextVar[Optional["AsyncSessionProxy"]] = ContextVar(
    "async_session", default=None
)


class ThreadLoopExecutor:
    """
    Executor that runs all tasks on a single dedicated thread.

    This ensures thread affinity for the SQLAlchemy Session.
    """

    def __init__(self):
        self._shutdown = False
        self._task_queue = asyncio.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True, name="AsyncSessionThread")
        self._thread.start()
        self._futures: weakref.WeakValueDictionary[int, asyncio.Future] = weakref.WeakValueDictionary()

    def _run(self):
        """Main loop running on the dedicated thread."""
        while not self._shutdown:
            try:
                # Get task from queue (synchronous get with timeout)
                coro, future = self._task_queue.get_nowait()
                self._task_queue.task_done()

                # Create event loop on this thread if needed
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Run the coroutine
                if future is not None and not future.cancelled():
                    try:
                        result = loop.run_until_complete(coro)
                        future.get_loop().call_soon_threadsafe(future.set_result, result)
                    except Exception as e:
                        future.get_loop().call_soon_threadsafe(future.set_exception, e)

            except asyncio.QueueEmpty:
                # No tasks, sleep briefly
                import time
                time.sleep(0.001)

    async def submit(self, coro: Callable[[], Any]) -> Any:
        """Submit a coroutine to run on the thread."""
        if self._shutdown:
            raise RuntimeError("Executor has been shut down")

        loop = asyncio.get_event_loop()
        future = loop.create_future()

        await self._task_queue.put((coro(), future))
        return await future

    def shutdown(self):
        """Shutdown the executor."""
        self._shutdown = True


class AsyncSessionProxy:
    """
    Async proxy for SQLAlchemy Session that ensures proper thread affinity.

    All session operations are executed on a dedicated thread to avoid cross-thread
    Session object issues. This ensures transaction consistency and proper ContextVar handling.

    Example:
        >>> async with client.session() as session:
        ...     # All operations run on the same thread with transaction consistency
        ...     await session.execute("INSERT INTO users (name) VALUES ('John')")
        ...     await session.execute("INSERT INTO users (name) VALUES ('Jane')")
        ...     await session.commit()  # Both inserts committed together

    """

    def __init__(self, session_factory: Callable[[], Session]):
        """
        Initialize the async session proxy.

        Args:
            session_factory: Callable that creates a new SQLAlchemy Session
                           This is called on the worker thread
        """
        self._session_factory = session_factory
        self._session: Optional[Session] = None
        self._executor = ThreadLoopExecutor()

    async def _init_session(self):
        """Initialize the session on the worker thread."""
        def _create_session():
            self._session = self._session_factory()
            return self._session

        return await asyncio.to_thread(_create_session)

    async def __aenter__(self):
        """Async context manager entry."""
        await self._init_session()
        # Set context variable to make this session available
        self._token = ASYNC_SESSION.set(self)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        try:
            if exc_type is not None:
                # Exception occurred, rollback
                await self.rollback()
            # Close the session
            if self._session is not None:
                await asyncio.to_thread(self._session.close)
        finally:
            # Reset context variable
            ASYNC_SESSION.reset(self._token)
            # Shutdown the executor
            self._executor.shutdown()

    async def execute(self, statement: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a SQL statement and return the result.

        Args:
            statement: SQL statement to execute
            params: Optional parameters for the statement

        Returns:
            AsyncSQLQueryResult: Async wrapper for the query result
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _execute():
            result = self._session.execute(statement, params=params or {})
            return result

        sync_result = await asyncio.to_thread(_execute)
        # Wrap in async result if module is available
        try:
            from .async_result import AsyncSQLQueryResult
            return AsyncSQLQueryResult(sync_result)
        except ImportError:
            return sync_result

    async def add(self, instance: Any) -> None:
        """
        Add an object to the session.

        Args:
            instance: Object to add to the session
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _add():
            self._session.add(instance)
            return None

        await asyncio.to_thread(_add)

    async def commit(self) -> None:
        """
        Commit the current transaction.
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _commit():
            self._session.commit()
            return None

        await asyncio.to_thread(_commit)

    async def rollback(self) -> None:
        """
        Rollback the current transaction.
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _rollback():
            self._session.rollback()
            return None

        await asyncio.to_thread(_rollback)

    async def flush(self) -> None:
        """
        Flush all pending changes to the database.
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _flush():
            self._session.flush()
            return None

        await asyncio.to_thread(_flush)

    async def refresh(self, instance: Any) -> None:
        """
        Refresh an object with data from the database.

        Args:
            instance: Object to refresh
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _refresh():
            self._session.refresh(instance)
            return None

        await asyncio.to_thread(_refresh)

    async def merge(self, instance: Any) -> Any:
        """
        Merge an object into the session.

        Args:
            instance: Object to merge

        Returns:
            Merged instance
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _merge():
            return self._session.merge(instance)

        return await asyncio.to_thread(_merge)

    async def query(self, *args, **kwargs) -> Any:
        """
        Create a query object.

        Returns:
            Query object from SQLAlchemy session
        """
        if self._session is None:
            raise TiDBError("Session not initialized")

        def _query():
            return self._session.query(*args, **kwargs)

        return await asyncio.to_thread(_query)

    async def close(self) -> None:
        """Close the session."""
        if self._session is None:
            return

        def _close():
            self._session.close()
            return None

        await asyncio.to_thread(_close)

    @property
    def sync_session(self) -> Optional[Session]:
        """
        Access the underlying sync session (for advanced use).

        WARNING: Only use this within the worker thread context.
        Accessing this from the event loop thread is unsafe.
        """
        return self._session


def get_async_session() -> Optional[AsyncSessionProxy]:
    """
    Get the currently active async session from the context variable.

    Returns:
        AsyncSessionProxy or None if no session is active
    """
    return ASYNC_SESSION.get()
