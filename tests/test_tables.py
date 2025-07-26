from typing import Optional
import pytest
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel
from pytidb.schema import Field


def test_open_table(isolated_client):
    class TestOpenTable(TableModel):
        __tablename__ = "test_open_table"
        id: int = Field(primary_key=True)
        name: str

    table = isolated_client.create_table(schema=TestOpenTable, if_exists="overwrite")
    table.truncate()
    table.insert(TestOpenTable(id=1, name="foo"))
    table = isolated_client.open_table("test_open_table")
    assert table.rows() == 1


def test_create_table_if_exists(isolated_client):
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

    isolated_client.create_table(schema=TestCreateTable, if_exists="skip")
    assert isolated_client.has_table(test_table_name)

    # if_exists=overwrite
    isolated_client.create_table(schema=TestCreateTable, if_exists="overwrite")
    assert isolated_client.has_table(test_table_name)

    # if_exists=invalid
    with pytest.raises(ValueError):
        isolated_client.create_table(schema=TestCreateTable, if_exists="invalid")


def test_save(isolated_client):
    text_embed_small = EmbeddingFunction("openai/text-embedding-3-small")
    test_table_name = "test_save_function"

    class TestModel(TableModel):
        __tablename__ = test_table_name
        id: int = Field(primary_key=True)
        text: str = Field()
        text_vec: Optional[list[float]] = text_embed_small.VectorField(
            source_field="text"
        )
        user_id: int = Field()

    tbl = isolated_client.create_table(schema=TestModel, if_exists="overwrite")

    # Test save - insert new record
    new_record = TestModel(id=1, text="hello world", user_id=1)
    saved_record = tbl.save(new_record)
    assert saved_record.id == 1
    assert saved_record.text == "hello world"

    # Test save - update existing record
    updated_record = TestModel(id=1, text="hello updated", user_id=1)
    saved_record = tbl.save(updated_record)
    assert saved_record.id == 1
    assert saved_record.text == "hello updated"

    # Test save with dict
    dict_record = {"id": 2, "text": "dict insert", "user_id": 2}
    saved_dict = tbl.save(dict_record)
    assert saved_dict.id == 2
    assert saved_dict.text == "dict insert"

    # Test save update with dict
    dict_update = {"id": 2, "text": "dict updated", "user_id": 2}
    saved_dict = tbl.save(dict_update)
    assert saved_dict.id == 2
    assert saved_dict.text == "dict updated"


def test_list_tables_empty(isolated_client):
    """Test list_tables on a fresh database with no tables."""

    # Should have no tables initially
    tables = isolated_client.list_tables()
    assert tables == []
    assert len(tables) == 0


def test_list_tables_with_tables(isolated_client):
    """Test list_tables after creating tables."""

    # Initially should have no tables
    tables = isolated_client.list_tables()
    assert tables == []

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
