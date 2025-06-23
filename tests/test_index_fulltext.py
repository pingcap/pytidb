import pytest
from pytidb import TiDBClient
from pytidb.orm.indexes import FullTextIndex
from pytidb.schema import TableModel, Field, TextField


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

    def test_auto_create_with_fulltext_field(self):
        class Chunk(TableModel):
            __tablename__ = "test_fulltext_index"
            id: int = Field(primary_key=True)
            text: str = TextField()

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_fts_index("text")

    def test_disable_auto_create_with_fulltext_field(self):
        class Chunk(TableModel):
            __tablename__ = "test_fulltext_index"
            id: int = Field(primary_key=True)
            text: str = TextField(index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert not tbl.has_fts_index("text")

    def test_create_with_fulltext_index(self):
        class Chunk(TableModel):
            __tablename__ = "test_fulltext_index"
            __table_args__ = (FullTextIndex("fts_idx_on_text", "text"),)
            id: int = Field(primary_key=True)
            text: str = TextField(index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_fts_index("text")

    def test_create_with_fulltext_field_and_index(self):
        class Chunk(TableModel):
            __tablename__ = "test_fulltext_index"
            __table_args__ = (FullTextIndex("fts_idx_on_text", "text"),)
            id: int = Field(primary_key=True)
            text: str = TextField(index=True)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        assert tbl.has_fts_index("text")

    def test_manual_create_with_fulltext_index(self):
        class Chunk(TableModel):
            __tablename__ = "test_fulltext_index"
            id: int = Field(primary_key=True)
            text: str = TextField(index=False)

        tbl = self.client.create_table(schema=Chunk, mode="overwrite")
        fts_idx = FullTextIndex("fts_idx_on_text", Chunk.text)
        fts_idx.create(self.client.db_engine)
        assert tbl.has_fts_index("text")
