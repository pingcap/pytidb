from typing import Type

from pytidb.schema import TableModel, Field, VectorField


def test_dynamic_table_creation(db):
    def get_chunk_model(tbl_name: str, dims: int) -> Type[TableModel]:
        class Chunk(TableModel):
            __tablename__ = tbl_name
            id: int = Field(primary_key=True)
            text: str = Field(max_length=20)
            text_vec: list[float] = VectorField(dimensions=dims)

        return Chunk

    chunk1 = get_chunk_model("chunks_1", 4)
    chunk2 = get_chunk_model("chunks_2", 5)
    tbl1 = db.create_table(schema=chunk1, mode="exist_ok")
    tbl2 = db.create_table(schema=chunk2, mode="exist_ok")

    columns1 = tbl1.columns()
    assert columns1[2].column_name == "text_vec"
    assert columns1[2].column_type == "vector(4)"

    columns2 = tbl2.columns()
    assert columns2[2].column_name == "text_vec"
    assert columns2[2].column_type == "vector(5)"

    tbl1.truncate()
    tbl2.truncate()
    tbl1.insert(chunk1(text="foo", text_vec=[1, 2, 3, 4]))
    tbl2.insert(chunk2(text="bar", text_vec=[5, 6, 7, 8, 9]))
    assert tbl1.rows() == 1
    assert tbl2.rows() == 1
