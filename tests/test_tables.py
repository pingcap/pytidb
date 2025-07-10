from typing import Optional
import pytest
from pytidb.embeddings import EmbeddingFunction
from pytidb.schema import TableModel
from pytidb.schema import Field


def test_open_table(client):
    class TestOpenTable(TableModel):
        __tablename__ = "test_open_table"
        id: int = Field(primary_key=True)
        name: str

    table = client.create_table(schema=TestOpenTable, mode="overwrite")
    table.truncate()
    table.insert(TestOpenTable(id=1, name="foo"))
    table = client.open_table("test_open_table")
    assert table.rows() == 1


def test_create_table_mode(client):
    test_table_name = "test_create_table"

    class TestCreateTable(TableModel):
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


def test_save(client):
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

    tbl = client.create_table(schema=TestModel, mode="overwrite")

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
