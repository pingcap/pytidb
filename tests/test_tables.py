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
