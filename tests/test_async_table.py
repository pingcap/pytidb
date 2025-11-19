from unittest.mock import AsyncMock, MagicMock

import pytest

from pytidb import table as table_module
from pytidb.table import Table


@pytest.fixture(autouse=True)
def run_sync_mock(monkeypatch):
    fake_run_sync = AsyncMock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
    monkeypatch.setattr(table_module, "run_sync", fake_run_sync)
    return fake_run_sync


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "async_method,sync_method,args,kwargs",
    [
        ("create_async", "create", tuple(), {"if_exists": "skip"}),
        ("drop_async", "drop", tuple(), {"if_not_exists": "skip"}),
        ("get_async", "get", (123,), {}),
        ("insert_async", "insert", ({"x": 1},), {}),
        ("save_async", "save", ({"y": 2},), {}),
        ("bulk_insert_async", "bulk_insert", ([{"z": 3}],), {}),
        ("update_async", "update", ({"z": 4},), {}),
        ("delete_async", "delete", tuple(), {"filters": {"a": 1}}),
        ("truncate_async", "truncate", tuple(), {}),
        ("columns_async", "columns", tuple(), {}),
        ("rows_async", "rows", tuple(), {}),
        ("query_async", "query", tuple(), {}),
    ],
)
async def test_table_async_methods_delegate(run_sync_mock, async_method, sync_method, args, kwargs):
    table = Table.__new__(Table)
    sentinel = object()

    setattr(table, sync_method, MagicMock(return_value=sentinel))

    result = await getattr(table, async_method)(*args, **kwargs)

    assert result is sentinel
    getattr(table, sync_method).assert_called_once_with(*args, **kwargs)
    assert run_sync_mock.await_count == 1
