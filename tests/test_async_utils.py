import pytest

from pytidb import utils


@pytest.mark.asyncio
async def test_run_sync_delegates_to_asyncio_to_thread(monkeypatch):
    called = {}

    async def fake_to_thread(func, *args, **kwargs):
        called["func"] = func
        called["args"] = args
        called["kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(utils.asyncio, "to_thread", fake_to_thread)

    def sample(a: int, b: int) -> int:
        return a + b

    result = await utils.run_sync(sample, 1, 2)

    assert result == 3
    assert called["func"] is sample
    assert called["args"] == (1, 2)
    assert called["kwargs"] == {}
