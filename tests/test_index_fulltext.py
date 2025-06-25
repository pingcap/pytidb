import pytest
from pytidb import TiDBClient
from pytidb.orm.indexes import FullTextIndex
from pytidb.schema import TableModel, Field, FullTextField


# Fulltext Index


class TestCreateFullTextIndex:
    """Test class for full text index functionality."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, client: TiDBClient):
        """Setup and teardown for each test method."""
        self.client = client
        yield
        # Cleanup: drop test table if it exists
        try:
            self.client.drop_table("test_fulltext_index")
        except Exception:
            pass

    def test_auto_create(self):
        class Chunk(TableModel):
            __tablename__ = "test_fts_index_auto_create"
            id: int = Field(primary_key=True)
            text: str = FullTextField()

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_fts_index("text")

    def test_auto_with_standard_parser(self):
        class Chunk(TableModel):
            __tablename__ = "test_fts_index_auto_with_standard_parser"
            id: int = Field(primary_key=True)
            text: str = FullTextField(index=True, fts_parser="STANDARD")

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_fts_index("text")

    def test_skip_create(self):
        class Chunk(TableModel):
            __tablename__ = "test_fts_index_skip_create"
            id: int = Field(primary_key=True)
            text: str = FullTextField(index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert not tbl.has_fts_index("text")

    def test_declare_with_index_cls(self):
        class Chunk(TableModel):
            __tablename__ = "test_fts_index_declare_index_cls"
            __table_args__ = (FullTextIndex("fts_idx_on_text", "text"),)
            id: int = Field(primary_key=True)
            text: str = FullTextField(index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_fts_index("text")

    def test_manual_with_table_api(self):
        class Chunk(TableModel):
            __tablename__ = "test_fts_index_manual_table_api"
            id: int = Field(primary_key=True)
            text: str = FullTextField(index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        tbl.create_fts_index("text")
        assert tbl.has_fts_index("text")

    def test_manual_with_table_api_exist_ok(self):
        class Chunk(TableModel):
            __tablename__ = "test_fts_index_manual_table_api_exists"
            id: int = Field(primary_key=True)
            text: str = FullTextField(index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        tbl.create_fts_index("text", exist_ok=True)
        assert tbl.has_fts_index("text")
