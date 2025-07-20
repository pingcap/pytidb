from typing import Any, Dict, List

import pytest
from sqlmodel import and_, or_

from pytidb.schema import TableModel, Field, Column
from pytidb.datatype import JSON
from pytidb.table import Table


class FilterTestCase:
    def __init__(self, name: str, filters: Dict[str, Any], expected: List[str]):
        self.name = name
        self.filters = filters
        self.expected = expected


class ChunkWithMeta(TableModel):
    __tablename__ = "test_filters_table"
    id: int = Field(primary_key=True)
    text: str = Field(max_length=20)
    document_id: int = Field()
    meta: Dict[str, Any] = Field(sa_column=Column(JSON))


@pytest.fixture(scope="module")
def test_filters_table(client):
    tbl = client.create_table(schema=ChunkWithMeta, if_exists="overwrite")

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

    return tbl


DICT_FILTER_TEST_CASES = [
    FilterTestCase(
        name="implicit $eq operator", filters={"document_id": 1}, expected=["foo"]
    ),
    FilterTestCase(
        name="explicit $eq operator",
        filters={"document_id": {"$eq": 1}},
        expected=["foo"],
    ),
    FilterTestCase(
        name="$in operator", filters={"id": {"$in": [2, 3]}}, expected=["bar", "biz"]
    ),
    FilterTestCase(
        name="$nin operator", filters={"id": {"$nin": [2, 3]}}, expected=["foo"]
    ),
    FilterTestCase(
        name="$gte operator", filters={"id": {"$gte": 2}}, expected=["bar", "biz"]
    ),
    FilterTestCase(name="$lt operator", filters={"id": {"$lt": 2}}, expected=["foo"]),
    FilterTestCase(
        name="$and operator",
        filters={"$and": [{"document_id": 2}, {"id": {"$gt": 2}}]},
        expected=["biz"],
    ),
    FilterTestCase(
        name="$or operator",
        filters={"$or": [{"document_id": 1}, {"id": 3}]},
        expected=["foo", "biz"],
    ),
    FilterTestCase(
        name="json column: $gt operator",
        filters={"meta.f": {"$gte": 0.5}},
        expected=["bar", "biz"],
    ),
    FilterTestCase(
        name="json column: explicit $eq operator",
        filters={"meta.s": {"$eq": "apple"}},
        expected=["foo"],
    ),
    FilterTestCase(
        name="json column: implicit $eq operator",
        filters={"meta.s": "apple"},
        expected=["foo"],
    ),
]


@pytest.mark.parametrize("test_case", DICT_FILTER_TEST_CASES, ids=lambda x: x.name)
def test_dict_filters(test_filters_table: Table, test_case: FilterTestCase):
    result = test_filters_table.query(test_case.filters).to_pydantic()
    actual = [r.text for r in result]
    assert actual == test_case.expected


SQL_FILTER_TEST_CASES = [
    FilterTestCase(name="equal operator", filters="document_id = 1", expected=["foo"]),
    FilterTestCase(name="in operator", filters="id IN (2, 3)", expected=["bar", "biz"]),
    FilterTestCase(
        name="not in operator", filters="id NOT IN (2, 3)", expected=["foo"]
    ),
    FilterTestCase(
        name="greater than or equal operator",
        filters="id >= 2",
        expected=["bar", "biz"],
    ),
    FilterTestCase(name="less than operator", filters="id < 2", expected=["foo"]),
    FilterTestCase(
        name="and operator", filters="document_id = 2 AND id > 2", expected=["biz"]
    ),
    FilterTestCase(
        name="or operator", filters="document_id = 1 OR id = 3", expected=["foo", "biz"]
    ),
    FilterTestCase(
        name="json column: greater than or equal operator",
        filters="JSON_EXTRACT(meta, '$.f') >= 0.5",
        expected=["bar", "biz"],
    ),
    FilterTestCase(
        name="json column: equal operator",
        filters="JSON_EXTRACT(meta, '$.s') = 'apple'",
        expected=["foo"],
    ),
]


@pytest.mark.parametrize("test_case", SQL_FILTER_TEST_CASES, ids=lambda x: x.name)
def test_sql_filters(test_filters_table: Table, test_case: FilterTestCase):
    result = test_filters_table.query(test_case.filters).to_pydantic()
    actual = [r.text for r in result]
    assert actual == test_case.expected


PYTHON_FILTER_TEST_CASES = [
    FilterTestCase(
        name="equal operator", filters=ChunkWithMeta.document_id == 1, expected=["foo"]
    ),
    FilterTestCase(
        name="in operator",
        filters=ChunkWithMeta.id.in_([2, 3]),
        expected=["bar", "biz"],
    ),
    FilterTestCase(
        name="not in operator",
        filters=ChunkWithMeta.id.notin_([2, 3]),
        expected=["foo"],
    ),
    FilterTestCase(
        name="greater than or equal operator",
        filters=ChunkWithMeta.id >= 2,
        expected=["bar", "biz"],
    ),
    FilterTestCase(
        name="less than operator", filters=ChunkWithMeta.id < 2, expected=["foo"]
    ),
    FilterTestCase(
        name="and operator",
        filters=and_(ChunkWithMeta.document_id == 2, ChunkWithMeta.id > 2),
        expected=["biz"],
    ),
    FilterTestCase(
        name="or operator",
        filters=or_(ChunkWithMeta.document_id == 1, ChunkWithMeta.id == 3),
        expected=["foo", "biz"],
    ),
    FilterTestCase(
        name="json column: greater than or equal operator",
        filters=ChunkWithMeta.meta["f"].as_float() >= 0.5,
        expected=["bar", "biz"],
    ),
    FilterTestCase(
        name="json column: equal operator",
        filters=ChunkWithMeta.meta["s"] == "apple",
        expected=["foo"],
    ),
]


@pytest.mark.parametrize("test_case", PYTHON_FILTER_TEST_CASES, ids=lambda x: x.name)
def test_python_filters(test_filters_table: Table, test_case: FilterTestCase):
    result = test_filters_table.query(test_case.filters).to_pydantic()
    actual = [r.text for r in result]
    assert actual == test_case.expected
