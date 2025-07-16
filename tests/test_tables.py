import pytest
from pytidb.schema import TableModel
from pytidb.schema import Field


def test_open_table(fresh_client):
    class TestOpenTable(TableModel):
        __tablename__ = "test_open_table"
        id: int = Field(primary_key=True)
        name: str

    table = fresh_client.create_table(schema=TestOpenTable, mode="overwrite")
    table.truncate()
    table.insert(TestOpenTable(id=1, name="foo"))
    table = fresh_client.open_table("test_open_table")
    assert table.rows() == 1


def test_create_table_mode(fresh_client):
    test_table_name = "test_create_table"

    class TestCreateTable(TableModel):
        __tablename__ = test_table_name
        id: int = Field(primary_key=True)
        name: str

    # create mode: raise_existing
    fresh_client.create_table(schema=TestCreateTable, mode="raise_existing")
    assert fresh_client.has_table(test_table_name)

    tables = fresh_client.list_tables()
    assert test_table_name in tables

    with pytest.raises(Exception):
        fresh_client.create_table(schema=TestCreateTable, mode="raise_existing")

    # create mode: skip_existing
    fresh_client.create_table(schema=TestCreateTable, mode="skip_existing")
    assert fresh_client.has_table(test_table_name)

    # create mode: overwrite
    fresh_client.create_table(schema=TestCreateTable, mode="overwrite")
    assert fresh_client.has_table(test_table_name)

    # create mode: invalid
    with pytest.raises(ValueError):
        fresh_client.create_table(schema=TestCreateTable, mode="invalid")


def test_list_tables_empty(fresh_client):
    """Test list_tables on a fresh database with no tables."""

    # Should have no tables initially
    tables = fresh_client.list_tables()
    assert tables == []
    assert len(tables) == 0


def test_list_tables_with_tables(fresh_client):
    """Test list_tables after creating tables."""

    # Initially should have no tables
    tables = fresh_client.list_tables()
    assert tables == []

    # Create first table
    class TestTable1(TableModel):
        __tablename__ = "test_table_1"
        id: int = Field(primary_key=True)
        name: str

    fresh_client.create_table(schema=TestTable1, mode="raise_existing")
    assert fresh_client.has_table("test_table_1")
    tables = fresh_client.list_tables()

    assert len(tables) == 1
    assert "test_table_1" in tables

    # Create second table
    class TestTable2(TableModel):
        __tablename__ = "test_table_2"
        id: int = Field(primary_key=True)
        value: int

    fresh_client.create_table(schema=TestTable2, mode="raise_existing")
    tables = fresh_client.list_tables()
    assert len(tables) == 2
    assert "test_table_1" in tables
    assert "test_table_2" in tables

    # Drop one table and verify
    fresh_client.drop_table("test_table_1")
    tables = fresh_client.list_tables()
    assert len(tables) == 1
    assert "test_table_1" not in tables
    assert "test_table_2" in tables

    # Drop remaining table
    fresh_client.drop_table("test_table_2")
    tables = fresh_client.list_tables()
    assert tables == []
