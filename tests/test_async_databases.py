from unittest.mock import AsyncMock

import pytest

from pytidb import databases


@pytest.mark.asyncio
async def test_create_database_async_uses_wrapper(monkeypatch):
    sentinel = object()
    fake_run_sync = AsyncMock(return_value=sentinel)
    monkeypatch.setattr(databases, "run_sync", fake_run_sync)

    result = await databases.create_database_async("engine", "demo", if_exists="skip")

    assert result is sentinel
    fake_run_sync.assert_awaited_once()
    args, kwargs = fake_run_sync.call_args
    assert args[0] is databases.create_database
    assert args[1:] == ("engine", "demo")
    assert kwargs == {"if_exists": "skip"}


@pytest.mark.asyncio
async def test_database_exists_async_uses_wrapper(monkeypatch):
    fake_run_sync = AsyncMock(return_value=True)
    monkeypatch.setattr(databases, "run_sync", fake_run_sync)

    result = await databases.database_exists_async("engine", "demo")

    assert result is True
    fake_run_sync.assert_awaited_once()
    call = fake_run_sync.call_args
    assert call.args[0] is databases.database_exists
    assert call.args[1:] == ("engine", "demo")
