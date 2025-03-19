import logging
from typing import Any, Dict, List

import numpy as np
import pytest

from pytidb.schema import TableModel, Field, VectorField
from pytidb.base import Base
from sqlalchemy import JSON, Column


logger = logging.getLogger(__name__)

# CRUD


def test_table_crud(db):
    table_name = "test_get_data"
    db.drop_table(table_name)

    class Chunk(TableModel, table=True):
        __tablename__ = table_name
        id: int = Field(primary_key=True)
        text: str = Field(max_length=20)
        text_vec: Any = VectorField(dimensions=3)

    tbl = db.create_table(schema=Chunk)

    # CREATE
    tbl.insert(Chunk(id=1, text="foo", text_vec=[1, 2, 3]))
    tbl.insert(Chunk(id=2, text="bar", text_vec=[4, 5, 6]))
    tbl.insert(Chunk(id=3, text="biz", text_vec=[7, 8, 9]))

    # RETRIEVE
    c = tbl.get(1)
    assert np.array_equal(c.text_vec, [1, 2, 3])

    # UPDATE
    tbl.update(
        values={
            "text": "fooooooo",
            "text_vec": [3, 6, 9],
        },
        filters={"text": "foo"},
    )
    c = tbl.get(1)
    assert c.text == "fooooooo"
    assert np.array_equal(c.text_vec, [3, 6, 9])

    # DELETE
    tbl.delete(filters={"id": {"$in": [1, 2]}})
    assert tbl.rows() == 1


# Test filters


@pytest.fixture(scope="module")
def table_for_test_filters(db):


    table_name = "test_query_data"
    db.drop_table(table_name)

    class ChunkWithMeta(TableModel, table=True):
        __tablename__ = table_name
        id: int = Field(primary_key=True)
        text: str = Field(max_length=20)
        document_id: int = Field()
        meta: Dict[str, Any] = Field(sa_column=Column(JSON))

    tbl = db.create_table(schema=ChunkWithMeta)
    Base.metadata.create_all(db.db_engine)

    test_data = [
        ChunkWithMeta(
            id=1,
            text="foo",
            document_id=1,
            meta={"f": 0.2, "s": "apple", "a": [1, 2, 3]},
        ),
        ChunkWithMeta(
            id=2,
            text="bar",
            document_id=2,
            meta={"f": 0.5, "s": "banana", "a": [4, 5, 6]},
        ),
        ChunkWithMeta(
            id=3,
            text="biz",
            document_id=2,
            meta={"f": 0.7, "s": "cherry", "a": [7, 8, 9]},
        ),
    ]

    tbl.bulk_insert(test_data)
    yield tbl
    db.drop_table(table_name)


filter_test_data = [
    pytest.param({"document_id": 1}, ["foo"], id="implicit $eq operator"),
    pytest.param({"document_id": {"$eq": 1}}, ["foo"], id="explicit $eq operator"),
    pytest.param({"id": {"$in": [2, 3]}}, ["bar", "biz"], id="$in operator"),
    pytest.param({"id": {"$nin": [2, 3]}}, ["foo"], id="$nin operator"),
    pytest.param({"id": {"$gte": 2}}, ["bar", "biz"], id="$gte operator"),
    pytest.param({"id": {"$lt": 2}}, ["foo"], id="$lt operator"),
    pytest.param(
        {"$and": [{"document_id": 2}, {"id": {"$gt": 2}}]}, ["biz"], id="$and operator"
    ),
    pytest.param(
        {"$or": [{"document_id": 1}, {"id": 3}]}, ["foo", "biz"], id="$or operator"
    ),
    pytest.param(
        {"meta.f": {"$gte": 0.5}}, ["bar", "biz"], id="json column: $gt operator"
    ),
    pytest.param({"meta.s": {"$eq": "apple"}}, ["foo"], id="json column: $eq operator"),
]


@pytest.mark.parametrize(
    "filters,expected",
    filter_test_data,
)
def test_filters(table_for_test_filters, filters: Dict[str, Any], expected: List[str]):
    tbl = table_for_test_filters
    result = tbl.query(filters)

    actual = [r.text for r in result]
    assert actual == expected

