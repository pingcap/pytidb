import pytest
from pytidb.schema import TableModel
from pytidb.schema import Field


def test_open_table(client):
    class TestOpenTable(TableModel, table=True):
        __tablename__ = "test_open_table"
        id: int = Field(primary_key=True)
        name: str

    table = client.create_table(schema=TestOpenTable)
    table.truncate()
    table.insert(TestOpenTable(id=1, name="foo"))
    table = client.open_table("test_open_table")
    assert table.rows() == 1


def test_create_table_mode(client):
    test_table_name = "test_create_table"

    class TestCreateTable(TableModel, table=True):
        __tablename__ = test_table_name
        id: int = Field(primary_key=True)
        name: str

    client.drop_table(test_table_name)

    # create mode: create
    client.create_table(schema=TestCreateTable, mode="create")
    assert client.has_table(test_table_name)

    with pytest.raises(Exception):
        client.create_table(schema=TestCreateTable, mode="create")

    # create mode: exist_ok
    client.create_table(schema=TestCreateTable, mode="exist_ok")
    assert client.has_table(test_table_name)

    # create mode: overwrite
    client.create_table(schema=TestCreateTable, mode="overwrite")
    assert client.has_table(test_table_name)
