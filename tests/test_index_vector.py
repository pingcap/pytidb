import pytest
from pytidb import TiDBClient
from pytidb.orm.indexes import VectorIndex
from pytidb.schema import TableModel, Field, VectorField


class TestCreateVectorIndex:
    """Test class for vector index functionality."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client: TiDBClient):
        """Setup and teardown for each test method."""
        self.client = client
        yield
        # Cleanup: drop test table if it exists
        try:
            self.client.drop_table("test_vector_index")
        except Exception:
            pass

    def test_auto_create_with_vector_field(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_auto_create"
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_auto_create_with_vector_field_l2(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_auto_create_l2"
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, distance_metric="L2")

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_skip_auto_create_with_vector_field(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_skip_auto_create"
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert not tbl.has_vector_index("text_vec")

    def test_create_with_index_cls(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_create_with_index_cls"
            __table_args__ = (VectorIndex("vec_idx_on_text_vec", "text_vec"),)
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_create_with_field_and_index_cls(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_create_with_field_and_index_cls"
            __table_args__ = (VectorIndex("vec_idx_on_text_vec", "text_vec"),)
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, index=True)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_create_with_field_and_index_cls_l2(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_create_with_field_and_index_cls_l2"
            __table_args__ = (
                VectorIndex("vec_idx_on_text_vec", "text_vec", distance_metric="L2"),
            )
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, index=True)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_manual_create_with_vector_index(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_manual_create"
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        vec_idx = VectorIndex("vec_idx_on_text_vec", Chunk.text_vec)
        vec_idx.create(self.client.db_engine)
        assert tbl.has_vector_index("text_vec")
