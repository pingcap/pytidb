import pytest
from pytidb import TiDBClient
from pytidb.orm.indexes import VectorIndex
from pytidb.orm.types import DistanceMetric
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

    def test_auto_create(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_auto_create"
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3)

        tbl = self.client.create_table(schema=Chunk, if_exists="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_auto_create_with_l2(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_auto_l2"
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(
                dimensions=3, distance_metric=DistanceMetric.L2
            )

        tbl = self.client.create_table(schema=Chunk, if_exists="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_declare_with_index_cls(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_declare_index_cls"
            __table_args__ = (VectorIndex("vec_idx_on_text_vec", "text_vec"),)
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, index=False)

        tbl = self.client.create_table(schema=Chunk, if_exists="overwrite")
        assert tbl.has_vector_index("text_vec")

    def test_manual_with_table_api(self):
        class Chunk(TableModel):
            __tablename__ = "test_vector_index_manual_table_api"
            id: int = Field(primary_key=True)
            text_vec: list[float] = VectorField(dimensions=3, index=False)

        tbl = self.client.create_table(schema=Chunk, if_exists="overwrite")
        tbl.create_vector_index("text_vec")
        assert tbl.has_vector_index("text_vec")
