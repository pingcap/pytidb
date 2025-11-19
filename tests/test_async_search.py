from unittest.mock import AsyncMock, MagicMock

import pytest

from pytidb import search as search_module
from pytidb.search import Search


@pytest.fixture(autouse=True)
def run_sync_mock(monkeypatch):
    fake_run_sync = AsyncMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
    monkeypatch.setattr(search_module, "run_sync", fake_run_sync)
    return fake_run_sync


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "async_method,sync_method",
    [
        ("to_rows_async", "to_rows"),
        ("to_list_async", "to_list"),
        ("to_pydantic_async", "to_pydantic"),
        ("to_pandas_async", "to_pandas"),
    ],
)
async def test_search_async_serialization_methods(run_sync_mock, async_method, sync_method):
    search = Search.__new__(Search)
    sentinel = object()
    setattr(search, sync_method, MagicMock(return_value=sentinel))

    result = await getattr(search, async_method)()

    assert result is sentinel
    getattr(search, sync_method).assert_called_once_with()
    assert run_sync_mock.await_count == 1


@pytest.mark.asyncio
async def test_search_execute_async(run_sync_mock):
    search = Search.__new__(Search)
    sentinel = (["col"], [{"value": 1}])
    search._execute_query = MagicMock(return_value=sentinel)

    result = await search.execute_async()

    assert result is sentinel
    search._execute_query.assert_called_once_with()
    assert run_sync_mock.await_count == 1
