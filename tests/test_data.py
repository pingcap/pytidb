import logging
from typing import Any, Optional
import numpy as np

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field, VectorField


logger = logging.getLogger(__name__)


def test_table_crud(shared_client):
    class Chunk(TableModel, table=True):
        __tablename__ = "test_table_crud"
        id: int = Field(primary_key=True)
        text: str = Field(max_length=20)
        text_vec: Any = VectorField(dimensions=3, index=False)

    tbl = shared_client.create_table(schema=Chunk, if_exists="overwrite")

    # CREATE
    tbl.insert(Chunk(id=1, text="foo", text_vec=[1, 2, 3]))
    tbl.bulk_insert(
        [
            Chunk(id=2, text="bar", text_vec=[4, 5, 6]),
            Chunk(id=3, text="biz", text_vec=[7, 8, 9]),
        ]
    )

    # RETRIEVE
    c = tbl.get(1)
    assert np.array_equal(c.text_vec, [1, 2, 3])

    # UPDATE
    updated_chunk = tbl.update(
        values={
            "text": "fooooooo",
            "text_vec": [3, 6, 9],
        },
        filters={"text": "foo"},
    )
    assert isinstance(updated_chunk, Chunk)
    assert updated_chunk.id == 1
    assert updated_chunk.text == "fooooooo"
    assert np.array_equal(updated_chunk.text_vec, [3, 6, 9])
    c = tbl.get(1)
    assert c.text == "fooooooo"
    assert np.array_equal(c.text_vec, [3, 6, 9])

    # DELETE
    tbl.delete(filters={"id": {"$in": [1, 2]}})
    assert tbl.rows() == 1

    # Columns
    columns = tbl.columns()
    assert len(columns) == 3
    assert columns[0].column_name == "id"
    assert columns[1].column_name == "text"
    assert columns[2].column_name == "text_vec"

    # Truncate
    tbl.truncate()
    assert tbl.rows() == 0


def test_table_update_returns_list_for_multiple_rows(shared_client):
    class Note(TableModel, table=True):
        __tablename__ = "test_table_update_returns_list"
        id: int = Field(primary_key=True)
        text: str = Field()

    tbl = shared_client.create_table(schema=Note, if_exists="overwrite")
    tbl.bulk_insert(
        [
            Note(id=1, text="a"),
            Note(id=2, text="b"),
        ]
    )

    updated_notes = tbl.update(
        values={"text": "updated"},
        filters={"id": {"$in": [1, 2]}},
    )

    assert isinstance(updated_notes, list)
    assert sorted(note.id for note in updated_notes) == [1, 2]
    assert {note.text for note in updated_notes} == {"updated"}


def test_table_update_returns_none_when_no_rows_match(shared_client):
    class Record(TableModel, table=True):
        __tablename__ = "test_table_update_returns_none"
        id: int = Field(primary_key=True)
        text: str = Field()

    tbl = shared_client.create_table(schema=Record, if_exists="overwrite")
    tbl.insert(Record(id=1, text="original"))

    result = tbl.update(values={"text": "updated"}, filters={"id": 2})
    assert result is None
    assert tbl.get(1).text == "original"


def test_table_update_returns_updated_instance_even_when_filter_field_changes(shared_client):
    class Message(TableModel, table=True):
        __tablename__ = "test_table_update_filter_field_change"
        id: int = Field(primary_key=True)
        text: str = Field()

    tbl = shared_client.create_table(schema=Message, if_exists="overwrite")
    tbl.insert(Message(id=1, text="old"))

    updated_message = tbl.update(values={"text": "new"}, filters={"text": "old"})

    assert isinstance(updated_message, Message)
    assert updated_message.id == 1
    assert updated_message.text == "new"


def test_table_update_returns_instance_when_primary_key_changes(shared_client):
    class Item(TableModel, table=True):
        __tablename__ = "test_table_update_pk_change"
        id: int = Field(primary_key=True)
        text: str = Field()

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.insert(Item(id=1, text="original"))

    updated_item = tbl.update(
        values={"id": 2, "text": "updated"},
        filters={"id": 1},
    )

    assert isinstance(updated_item, Item)
    assert updated_item.id == 2
    assert updated_item.text == "updated"
    assert tbl.get(1) is None
    assert tbl.get(2).text == "updated"


def test_table_query(shared_client):
    class Chunk(TableModel):
        __tablename__ = "test_table_query"
        id: int = Field(primary_key=True)
        text: str = Field(max_length=20)
        text_vec: Any = VectorField(dimensions=3, index=False)

    tbl = shared_client.create_table(schema=Chunk, if_exists="overwrite")

    tbl.insert(Chunk(id=1, text="foo", text_vec=[1, 2, 3]))
    tbl.insert(Chunk(id=2, text="bar", text_vec=[4, 5, 6]))
    tbl.insert(Chunk(id=3, text="biz", text_vec=[7, 8, 9]))

    # Pagination

    result = tbl.query(limit=1, order_by="id")
    assert len(result.to_list()) == 1

    result = tbl.query(limit=1, offset=1, order_by="id")
    assert len(result.to_list()) == 1
    assert result.to_list()[0]["id"] == 2

    # ORDER BY

    result = tbl.query(order_by="id", limit=1)
    assert result.to_list()[0]["id"] == 1

    result = tbl.query(order_by={"id": "desc"}, limit=1)
    assert result.to_list()[0]["id"] == 3

    result = tbl.query(order_by={"id": "asc"}, limit=1)
    assert result.to_list()[0]["id"] == 1

    # To pydantic

    result = tbl.query(order_by="id", limit=1)
    chunks = result.to_pydantic()
    assert len(chunks) == 1
    assert chunks[0].id == 1
    assert chunks[0].text == "foo"
    assert np.array_equal(chunks[0].text_vec, [1, 2, 3])

    # To pandas

    result = tbl.query(order_by="id", limit=1)
    chunks = result.to_pandas()
    assert len(chunks) == 1
    assert chunks.iloc[0]["id"] == 1
    assert chunks.iloc[0]["text"] == "foo"
    assert np.array_equal(chunks.iloc[0]["text_vec"], [1, 2, 3])

    # To list

    result = tbl.query(order_by="id", limit=1)
    chunks = result.to_list()
    assert len(chunks) == 1
    assert chunks[0]["id"] == 1
    assert chunks[0]["text"] == "foo"
    assert np.array_equal(chunks[0]["text_vec"], [1, 2, 3])


def test_table_save(shared_client: TiDBClient):
    class RecordForSaveData(TableModel):
        __tablename__ = "test_table_save"
        id: int = Field(primary_key=True)
        text: str = Field()
        text_vec: Optional[list[float]] = VectorField(dimensions=3)
        user_id: int = Field()

    Record = RecordForSaveData

    tbl = shared_client.create_table(schema=Record, if_exists="overwrite")

    # Test save - insert new record
    new_record = Record(id=1, text="hello world", user_id=1)
    saved_record = tbl.save(new_record)
    assert saved_record.id == 1
    assert saved_record.text == "hello world"

    # Test save - update existing record
    updated_record = Record(id=1, text="hello updated", user_id=1)
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
