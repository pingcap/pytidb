import os

import pytest

SKIP_TIDB_TESTS = os.getenv("PYTIDB_SKIP_TIDB_TESTS", "").lower() in (
    "1",
    "true",
    "yes",
)

pytestmark = pytest.mark.skipif(
    not SKIP_TIDB_TESTS,
    reason="PYTIDB_SKIP_TIDB_TESTS is not enabled",
)


def _assert_stub(client):
    assert client.__class__.__name__ == "_StubTiDBClient"
    assert client.__class__.__module__.endswith("conftest")
    assert "PYTIDB_SKIP_TIDB_TESTS" in getattr(client, "skip_reason", "")


def test_shared_client_stub_skips_method_calls(shared_client):
    _assert_stub(shared_client)

    with pytest.raises(pytest.skip.Exception):
        shared_client.create_table(schema=None)


def test_shared_client_stub_skips_attribute_access(shared_client):
    _assert_stub(shared_client)

    with pytest.raises(pytest.skip.Exception):
        _ = shared_client.is_serverless


def test_isolated_client_uses_stub(isolated_client):
    _assert_stub(isolated_client)

    with pytest.raises(pytest.skip.Exception):
        isolated_client.drop_database("foo")
