from pydantic import BaseModel
from sqlalchemy import insert

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.sql import select


def test_raw_sql(shared_client: TiDBClient):
    result = shared_client.execute("DROP TABLE IF EXISTS test_raw_sql;")
    assert result.success
    assert result.rowcount == 0

    result = shared_client.execute("CREATE TABLE IF NOT EXISTS test_raw_sql(id int);")
    assert result.success
    assert result.rowcount == 0

    result = shared_client.execute("CREATE TABLE test_raw_sql(id int);")
    assert not result.success
    assert result.rowcount == 0
    assert result.message is not None

    result = shared_client.execute("INSERT INTO test_raw_sql VALUES (1), (2), (3);")
    assert result.success
    assert result.rowcount == 3

    # to_pandas
    result = shared_client.query("SELECT id FROM test_raw_sql;")
    df = result.to_pandas()
    assert df.size == 3

    # to_rows
    result = shared_client.query("SELECT id FROM test_raw_sql;")
    rows = result.to_rows()
    ids = sorted([r[0] for r in rows])
    assert ids == [1, 2, 3]

    # to_list
    result = shared_client.query("SELECT id FROM test_raw_sql;")
    list = result.to_list()
    ids = sorted([item["id"] for item in list])
    assert ids == [1, 2, 3]

    # to_pydantic
    class Record(BaseModel):
        id: int

    result = shared_client.query("SELECT id FROM test_raw_sql;")
    records = result.to_pydantic(Record)
    ids = sorted([r.id for r in records])
    assert ids == [1, 2, 3]

    # scalar
    result = shared_client.query("SELECT COUNT(*) FROM test_raw_sql;")
    n = result.scalar()
    assert n == 3


def test_query_select_base(shared_client: TiDBClient):
    class Record(TableModel, table=True):
        __tablename__ = "test_query_select_base"
        id: int = Field(default=None, primary_key=True)
        name: str = Field(default=None)

    tbl = shared_client.create_table(schema=Record, if_exists="overwrite")

    # Insert data via execute()
    stmt = insert(tbl.table_model).values(id=1, name="test")
    result = shared_client.execute(stmt)
    assert result.success

    # Query data via query()
    stmt = select(tbl.table_model.id).where(tbl.table_model.id == 1)
    result = shared_client.query(stmt)
    assert result.to_list() == [{"id": 1}]

    shared_client.drop_table(tbl.table_name)
