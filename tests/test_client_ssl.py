from types import SimpleNamespace
from sqlalchemy.engine import make_url

from pytidb import TiDBClient
import pytidb.client as client_module


class DummyEngine:
    def __init__(self, url: str):
        self.url = make_url(url)
        self.dialect = SimpleNamespace(identifier_preparer=object())

    def dispose(self) -> None:
        pass


def patch_create_engine(monkeypatch, captured):
    def _fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return DummyEngine(url)

    monkeypatch.setattr(client_module, "create_engine", _fake_create_engine)


def test_connect_injects_ca_path_into_connect_args(monkeypatch):
    captured = {}
    patch_create_engine(monkeypatch, captured)

    ca_path = "/tmp/isrgrootx1.pem"
    client = TiDBClient.connect(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="u",
        password="p",
        database="db",
        ca_path=ca_path,
    )

    ssl_args = captured["kwargs"]["connect_args"]["ssl"]
    assert ssl_args == {"ca": ca_path}
    assert client._reconnect_params.get("ca_path") == ca_path


def test_connect_merges_existing_ssl_options(monkeypatch):
    captured = {}
    patch_create_engine(monkeypatch, captured)

    ca_path = "/tmp/isrgrootx1.pem"
    existing = {"ssl": {"cert": "client-cert"}}

    TiDBClient.connect(
        host="gateway01.us-west-2.prod.aws.tidbcloud.com",
        username="u",
        password="p",
        database="db",
        ca_path=ca_path,
        connect_args=existing,
    )

    ssl_args = captured["kwargs"]["connect_args"]["ssl"]
    assert ssl_args["cert"] == "client-cert"
    assert ssl_args["ca"] == ca_path
    assert "ca" not in existing["ssl"]


def test_connect_without_ca_path_leaves_connect_args_untouched(monkeypatch):
    captured = {}
    patch_create_engine(monkeypatch, captured)

    TiDBClient.connect(
        host="127.0.0.1",
        username="root",
        password="",
        database="test",
    )

    assert "connect_args" not in captured["kwargs"]


def test_connect_enables_ssl_when_ca_path_set(monkeypatch):
    captured = {}
    patch_create_engine(monkeypatch, captured)
    ca_path = "/tmp/isrgrootx1.pem"

    TiDBClient.connect(
        host="localhost",
        username="root",
        password="",
        database="test",
        ca_path=ca_path,
    )

    assert "ssl_verify_cert=true" in captured["url"]
