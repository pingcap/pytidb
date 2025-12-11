import copy

import pytest
from sqlalchemy.engine import make_url

from pytidb import TiDBClient


class DummyDialect:
    identifier_preparer = object()


class DummyEngine:
    def __init__(self, url: str):
        self.url = make_url(url)
        self.dialect = DummyDialect()

    def dispose(self):
        pass


@pytest.fixture
def capture_engine_calls(monkeypatch):
    calls = []

    def fake_create_engine(url, **kwargs):
        calls.append({"url": url, "kwargs": kwargs})
        return DummyEngine(url)

    monkeypatch.setattr("pytidb.client.create_engine", fake_create_engine)
    return calls


def test_connect_injects_ca_path_into_ssl_kwargs(capture_engine_calls):
    TiDBClient.connect(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="root",
        password="",
        database="test",
        ca_path="/tmp/isrgrootx1.pem",
    )

    assert capture_engine_calls, "create_engine was not called"
    connect_args = capture_engine_calls[0]["kwargs"].get("connect_args")
    assert connect_args is not None
    assert connect_args["ssl"]["ca"] == "/tmp/isrgrootx1.pem"


def test_connect_merges_existing_connect_args(capture_engine_calls):
    original_args = {"some_option": 42, "ssl": {"cert": "/tmp/cert.pem"}}

    TiDBClient.connect(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="root",
        password="",
        database="test",
        ca_path="/tmp/isrgrootx1.pem",
        connect_args=copy.deepcopy(original_args),
    )

    connect_args = capture_engine_calls[0]["kwargs"]["connect_args"]
    assert connect_args["some_option"] == 42
    assert connect_args["ssl"]["cert"] == "/tmp/cert.pem"
    assert connect_args["ssl"]["ca"] == "/tmp/isrgrootx1.pem"
    # Ensure we did not mutate the original dict object
    assert original_args["ssl"].get("ca") is None


def test_connect_leaves_kwargs_unmodified_when_no_ca_path(capture_engine_calls):
    TiDBClient.connect(
        host="localhost",
        username="root",
        password="",
        database="test",
    )

    kwargs = capture_engine_calls[0]["kwargs"]
    assert "connect_args" not in kwargs
