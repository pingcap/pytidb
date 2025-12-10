from types import SimpleNamespace
from sqlalchemy.engine import make_url

from pytidb.client import TiDBClient


class DummyIdentifierPreparer:
    def quote(self, value):
        return value


class DummyEngine:
    def __init__(self, url: str):
        self.url = make_url(url)
        self.dialect = SimpleNamespace(identifier_preparer=DummyIdentifierPreparer())

    def dispose(self):
        pass


def build_fake_engine(capture: dict):
    def _fake_create_engine(url, echo=False, **kwargs):
        capture["url"] = url
        capture["kwargs"] = kwargs
        capture["echo"] = echo
        return DummyEngine(url)

    return _fake_create_engine


def test_connect_uses_env_ca_path(monkeypatch):
    capture: dict = {}
    monkeypatch.setenv("TIDB_CA_PATH", "/tmp/isrgrootx1.pem")
    monkeypatch.setattr("pytidb.client.create_engine", build_fake_engine(capture))

    client = TiDBClient.connect(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="user",
        password="pass",
        database="test_db",
    )

    assert capture["kwargs"]["connect_args"]["ssl"]["ca"] == "/tmp/isrgrootx1.pem"
    assert client.is_serverless is True


def test_connect_without_ca_path_leaves_connect_args(monkeypatch):
    capture: dict = {}
    monkeypatch.delenv("TIDB_CA_PATH", raising=False)
    monkeypatch.setattr("pytidb.client.create_engine", build_fake_engine(capture))

    client = TiDBClient.connect(
        host="127.0.0.1",
        username="user",
        password="pass",
        database="test_db",
    )

    assert "connect_args" not in capture["kwargs"]
    assert client.is_serverless is False
