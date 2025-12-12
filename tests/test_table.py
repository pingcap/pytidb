from pytidb.schema import Field, TableModel


def test_table_update_returns_single_instance(shared_client):
    class Item(TableModel):
        __tablename__ = "test_update_returns_single_instance"
        id: int = Field(primary_key=True)
        text: str = Field(max_length=50)

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.insert(Item(id=1, text="before"))

    updated = tbl.update(values={"text": "after"}, filters={"id": 1})

    assert isinstance(updated, Item)
    assert updated.id == 1
    assert updated.text == "after"


def test_table_update_returns_multiple_instances(shared_client):
    class Item(TableModel):
        __tablename__ = "test_update_returns_multiple_instances"
        id: int = Field(primary_key=True)
        balance: int = Field(default=0)

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.bulk_insert([Item(id=1, balance=1), Item(id=2, balance=2), Item(id=3, balance=3)])

    updated = tbl.update(values={"balance": 42}, filters={"id": {"$in": [1, 2]}})

    assert isinstance(updated, list)
    assert {item.id for item in updated} == {1, 2}
    assert all(item.balance == 42 for item in updated)


def test_table_update_returns_none_when_no_matches(shared_client):
    class Item(TableModel):
        __tablename__ = "test_update_returns_none_when_no_matches"
        id: int = Field(primary_key=True)
        text: str = Field(max_length=50)

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.insert(Item(id=1, text="before"))

    updated = tbl.update(values={"text": "after"}, filters={"id": 999})

    assert updated is None


def test_table_update_empty_values_is_noop_and_returns_instance(shared_client):
    class Item(TableModel):
        __tablename__ = "test_update_empty_values_is_noop_and_returns_instance"
        id: int = Field(primary_key=True)
        text: str = Field(max_length=50)

    tbl = shared_client.create_table(schema=Item, if_exists="overwrite")
    tbl.insert(Item(id=1, text="before"))

    updated = tbl.update(values={}, filters={"id": 1})

    assert isinstance(updated, Item)
    assert updated.id == 1
    assert updated.text == "before"
