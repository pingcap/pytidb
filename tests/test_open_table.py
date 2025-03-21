from pytidb.schema import TableModel, Field


def test_open_table(db):
    class TestOpenTable(TableModel, table=True):
        __tablename__ = "test_open_table"
        id: int = Field(primary_key=True)
        name: str

    table = db.create_table(schema=TestOpenTable)
    table.truncate()
    table.insert(TestOpenTable(id=1, name="foo"))
    table = db.open_table("test_open_table")
    assert table.rows() == 1
