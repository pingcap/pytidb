import pytest

from pytidb.schema import TableModel, Field


def test_table_update_returns_updated_instances(shared_client):
    class Item(TableModel, table=True):
        __tablename__ = "test_table_update_returns_updated_instances"
        id: int = Field(primary_key=True)
        name: str

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.bulk_insert(
        [
            Item(id=1, name="a"),
            Item(id=2, name="b"),
            Item(id=3, name="c"),
        ]
    )

    updated = tbl.update(values={"name": "z"}, filters={"id": {"$in": [1, 2]}})
    assert isinstance(updated, list)
    assert {item.id for item in updated} == {1, 2}
    assert all(item.name == "z" for item in updated)

    assert tbl.get(1).name == "z"
    assert tbl.get(2).name == "z"
    assert tbl.get(3).name == "c"


def test_table_update_no_matches_returns_empty_list(shared_client):
    class Item(TableModel, table=True):
        __tablename__ = "test_table_update_no_matches_returns_empty_list"
        id: int = Field(primary_key=True)
        name: str

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.insert(Item(id=1, name="a"))

    updated = tbl.update(values={"name": "z"}, filters={"id": 999})
    assert updated == []


def test_table_update_empty_values_raises(shared_client):
    class Item(TableModel, table=True):
        __tablename__ = "test_table_update_empty_values_raises"
        id: int = Field(primary_key=True)
        name: str

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.insert(Item(id=1, name="a"))

    with pytest.raises(ValueError):
        tbl.update(values={}, filters={"id": 1})
