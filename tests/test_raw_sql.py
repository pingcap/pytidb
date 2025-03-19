from pydantic import BaseModel

from pytidb import TiDBClient


def test_raw_sql(db: TiDBClient):
    result = db.execute("DROP TABLE IF EXISTS test_raw_sql;")
    assert result.success
    assert result.rowcount == 0

    result = db.execute("CREATE TABLE IF NOT EXISTS test_raw_sql(id int);")
    assert result.success
    assert result.rowcount == 0

    result = db.execute("CREATE TABLE test_raw_sql(id int);")
    assert not result.success
    assert result.rowcount == 0
    assert result.message is not None

    result = db.execute("INSERT INTO test_raw_sql VALUES (1), (2), (3);")
    assert result.success
    assert result.rowcount == 3

    result = db.query("SELECT id FROM test_raw_sql;")
    df = result.to_pandas()
    assert df.size == 3

    result = db.query("SELECT id FROM test_raw_sql;")
    rows = result.to_rows()
    ids = sorted([r[0] for r in rows])
    assert ids == [1, 2, 3]

    result = db.query("SELECT id FROM test_raw_sql;")
    list = result.to_list()
    ids = sorted([item["id"] for item in list])
    assert ids == [1, 2, 3]

    class Record(BaseModel):
        id: int

    result = db.query("SELECT id FROM test_raw_sql;")
    records = result.to_pydantic(Record)
    ids = sorted([r.id for r in records])
    assert ids == [1, 2, 3]

    result = db.query("SELECT COUNT(*) FROM test_raw_sql;")
    n = result.scalar()
    assert n == 3
