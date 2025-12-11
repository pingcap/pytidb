from unittest.mock import MagicMock

from sqlalchemy import create_engine

from pytidb.schema import Field, TableModel
from pytidb.table import Table


class DummyModel(TableModel, table=True):
    __tablename__ = "table_update_returns_instance"

    id: int = Field(primary_key=True)
    text: str = Field(default="")


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class _StubClient:
    def __init__(self, session):
        self._db_engine = create_engine("sqlite://")
        self._session = session

    @property
    def db_engine(self):
        return self._db_engine

    def session(self, *_, **__):
        return _SessionContext(self._session)


def test_update_returns_single_instance():
    mock_session = MagicMock()
    client = _StubClient(mock_session)
    table = Table(client=client, schema=DummyModel)

    updated = DummyModel(id=1, text="before")
    exec_result = MagicMock()
    exec_result.all.return_value = [updated]
    mock_session.exec.return_value = exec_result

    returned = table.update({"text": "after"}, {"id": 1})

    assert returned is updated
    mock_session.refresh.assert_called_once_with(updated)
    mock_session.execute.assert_called()


def test_update_returns_multiple_instances_as_list():
    mock_session = MagicMock()
    client = _StubClient(mock_session)
    table = Table(client=client, schema=DummyModel)

    updated_rows = [
        DummyModel(id=1, text="before-1"),
        DummyModel(id=2, text="before-2"),
    ]
    exec_result = MagicMock()
    exec_result.all.return_value = updated_rows
    mock_session.exec.return_value = exec_result

    returned = table.update({"text": "after"}, {"id": {"$in": [1, 2]}})

    assert returned == updated_rows
    assert mock_session.refresh.call_count == 2
    mock_session.execute.assert_called()


def test_update_returns_none_when_no_match():
    mock_session = MagicMock()
    client = _StubClient(mock_session)
    table = Table(client=client, schema=DummyModel)

    exec_result = MagicMock()
    exec_result.all.return_value = []
    mock_session.exec.return_value = exec_result

    returned = table.update({"text": "after"}, {"id": 99})

    assert returned is None
    mock_session.refresh.assert_not_called()
    mock_session.execute.assert_called()
