from types import SimpleNamespace

import pytest
from sqlalchemy.engine import make_url

from pytidb import TiDBClient


class _DummyEngine:
    def __init__(self, url: str):
        self.url = make_url(url)
        self.dialect = SimpleNamespace(identifier_preparer=SimpleNamespace())

    def dispose(self) -> None:  # pragma: no cover - trivial stub
        pass


@pytest.fixture
def _engine_recorder(monkeypatch):
    recorded = {}

    def _fake_create_engine(url, **kwargs):
        recorded["kwargs"] = kwargs
        return _DummyEngine(url)

    monkeypatch.setattr("pytidb.client.create_engine", _fake_create_engine)
    return recorded


def _connect(**kwargs):
    client = TiDBClient.connect(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        port=4000,
        username="user",
        password="pass",
        database="test",
        **kwargs,
    )
    client.disconnect()
    return client


def test_connect_passes_ca_path(_engine_recorder):
    _connect(ca_path="/tmp/isrgrootx1.pem")

    connect_args = _engine_recorder["kwargs"].get("connect_args")
    assert connect_args["ssl_ca"] == "/tmp/isrgrootx1.pem"


def test_connect_merges_existing_connect_args(_engine_recorder):
    _connect(ca_path="/tmp/custom.pem", connect_args={"charset": "utf8mb4"})

    connect_args = _engine_recorder["kwargs"].get("connect_args")
    assert connect_args["ssl_ca"] == "/tmp/custom.pem"
    assert connect_args["charset"] == "utf8mb4"


def test_connect_without_ca_path_leaves_connect_args_optional(_engine_recorder):
    _connect()

    assert "connect_args" not in _engine_recorder["kwargs"]
