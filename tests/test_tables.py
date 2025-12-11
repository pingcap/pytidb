import pytest
from pytidb.client import TiDBClient
from pytidb.schema import TableModel
from pytidb.schema import Field


def test_create_table(isolated_client: TiDBClient):
    test_table_name = "test_create_table"

    class TestCreateTable(TableModel):
        __tablename__ = test_table_name
        id: int = Field(primary_key=True)
        name: str

    # if_exists=raise
    isolated_client.create_table(schema=TestCreateTable, if_exists="raise")
    assert isolated_client.has_table(test_table_name)

    tables = isolated_client.list_tables()
    assert test_table_name in tables

    with pytest.raises(Exception):
        isolated_client.create_table(schema=TestCreateTable, if_exists="raise")

    # if_exists=skip
    isolated_client.create_table(schema=TestCreateTable, if_exists="skip")
    assert isolated_client.has_table(test_table_name)

    # if_exists=overwrite
    isolated_client.create_table(schema=TestCreateTable, if_exists="overwrite")
    assert isolated_client.has_table(test_table_name)

    # if_exists=invalid
    with pytest.raises(ValueError):
        isolated_client.create_table(schema=TestCreateTable, if_exists="invalid")


def test_open_table(isolated_client: TiDBClient):
    class TestOpenTable(TableModel):
        __tablename__ = "test_open_table"
        id: int = Field(primary_key=True)
        name: str

    table = isolated_client.create_table(schema=TestOpenTable, if_exists="overwrite")
    table.truncate()
    table.insert(TestOpenTable(id=1, name="foo"))
    table = isolated_client.open_table("test_open_table")
    assert table.rows() == 1


def test_list_tables(isolated_client: TiDBClient):
    """Test list_tables after creating tables."""

    # Initially should have no tables
    tables = isolated_client.list_tables()
    assert tables == []
    assert len(tables) == 0

    # Create first table
    class TestTable1(TableModel):
        __tablename__ = "test_table_1"
        id: int = Field(primary_key=True)
        name: str

    isolated_client.create_table(schema=TestTable1, if_exists="raise")
    assert isolated_client.has_table("test_table_1")
    tables = isolated_client.list_tables()

    assert len(tables) == 1
    assert "test_table_1" in tables

    # Create second table
    class TestTable2(TableModel):
        __tablename__ = "test_table_2"
        id: int = Field(primary_key=True)
        value: int

    isolated_client.create_table(schema=TestTable2, if_exists="raise")
    tables = isolated_client.list_tables()
    assert len(tables) == 2
    assert "test_table_1" in tables
    assert "test_table_2" in tables

    # Drop one table and verify
    isolated_client.drop_table("test_table_1")
    tables = isolated_client.list_tables()
    assert len(tables) == 1
    assert "test_table_1" not in tables
    assert "test_table_2" in tables

    # Drop remaining table
    isolated_client.drop_table("test_table_2")
    tables = isolated_client.list_tables()
    assert tables == []


def test_drop_table(isolated_client: TiDBClient):
    """Test drop_table functionality with different if_not_exists options."""
    test_table_name = "test_drop_table"

    class TestDropTable(TableModel):
        __tablename__ = test_table_name
        id: int = Field(primary_key=True)
        name: str

    # Create a table first
    isolated_client.create_table(schema=TestDropTable)
    assert isolated_client.has_table(test_table_name)

    # Test drop_table with if_not_exists="raise" (default)
    isolated_client.drop_table(test_table_name)
    assert not isolated_client.has_table(test_table_name)

    # Test drop_table on non-existent table with if_not_exists="raise" should raise exception
    with pytest.raises(Exception):
        isolated_client.drop_table(test_table_name, if_not_exists="raise")

    # Test drop_table on non-existent table with if_not_exists="skip" should not raise exception
    isolated_client.drop_table(test_table_name, if_not_exists="skip")
    assert not isolated_client.has_table(test_table_name)

    # Test invalid if_not_exists value
    with pytest.raises(ValueError):
        isolated_client.drop_table(test_table_name, if_not_exists="invalid")


def test_table_update_returns_instance_single_field(isolated_client: TiDBClient):
    class UpdateSingleField(TableModel):
        __tablename__ = "test_update_single_field"
        id: int = Field(primary_key=True)
        name: str
        balance: int

    table = isolated_client.create_table(schema=UpdateSingleField, if_exists="overwrite")
    table.truncate()
    table.insert(UpdateSingleField(id=1, name="Alice", balance=100))

    updated = table.update({"name": "Bob"}, {"id": 1})

    assert isinstance(updated, UpdateSingleField)
    assert updated.id == 1
    assert updated.name == "Bob"
    assert updated.balance == 100
    assert table.get(1).name == "Bob"


def test_table_update_returns_instance_multiple_fields(isolated_client: TiDBClient):
    class UpdateMultipleFields(TableModel):
        __tablename__ = "test_update_multiple_fields"
        id: int = Field(primary_key=True)
        name: str
        balance: int

    table = isolated_client.create_table(
        schema=UpdateMultipleFields, if_exists="overwrite"
    )
    table.truncate()
    table.insert(UpdateMultipleFields(id=1, name="Alice", balance=100))

    updated = table.update({"name": "Charlie", "balance": 250}, {"id": 1})

    assert isinstance(updated, UpdateMultipleFields)
    assert updated.id == 1
    assert updated.name == "Charlie"
    assert updated.balance == 250
    reloaded = table.get(1)
    assert reloaded.name == "Charlie"
    assert reloaded.balance == 250


def test_table_update_returns_none_when_no_rows_match(isolated_client: TiDBClient):
    class UpdateNoMatch(TableModel):
        __tablename__ = "test_update_no_match"
        id: int = Field(primary_key=True)
        name: str

    table = isolated_client.create_table(schema=UpdateNoMatch, if_exists="overwrite")
    table.truncate()
    table.insert(UpdateNoMatch(id=1, name="Alice"))

    updated = table.update({"name": "Bob"}, {"id": 999})

    assert updated is None
    assert table.get(1).name == "Alice"
