import pytest
from sqlalchemy import Table, Column, Integer, String, MetaData
from pytidb import TiDBClient
from pytidb.orm.tiflash_replica import TiFlashReplica
from pytidb.schema import TableModel, Field
from tests.conftest import generate_dynamic_name


class TestTiFlashReplicaWithSATable:
    """Test TiFlash replica functionality with SQLAlchemy Table."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, isolated_client: TiDBClient):
        self.client = isolated_client
        yield
        self.client = None

    def _create_test_table(self) -> Table:
        """Create a test table with a unique name for each test."""
        table_name = generate_dynamic_name("test_tiflash_sa_table")
        metadata = MetaData()
        test_table = Table(
            table_name,
            metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String(50)),
            Column("value", Integer),
        )
        test_table.create(self.client.db_engine, checkfirst=True)
        return test_table

    def test_create_replica(self):
        test_table = self._create_test_table()
        try:
            replica = TiFlashReplica(test_table, replica_count=1)
            replica.create(self.client.db_engine)
            progress = replica.get_replication_progress(self.client.db_engine)
            assert progress["table_name"] == test_table.name
        finally:
            test_table.drop(self.client.db_engine, checkfirst=True)

    def test_drop_replica(self):
        test_table = self._create_test_table()
        try:
            replica = TiFlashReplica(test_table, replica_count=1)
            replica.drop(self.client.db_engine)
            progress = replica.get_replication_progress(self.client.db_engine)
            assert progress["replica_count"] == 0
        finally:
            test_table.drop(self.client.db_engine, checkfirst=True)

    def test_get_replication_progress(self):
        test_table = self._create_test_table()
        try:
            replica = TiFlashReplica(test_table, replica_count=1)
            progress = replica.get_replication_progress(self.client.db_engine)
            assert progress["table_name"] == test_table.name
            assert progress["replica_count"] == 0
            assert not progress["available"]
        finally:
            test_table.drop(self.client.db_engine, checkfirst=True)

    def test_invalid_replica_count(self):
        test_table = self._create_test_table()
        try:
            with pytest.raises(ValueError, match="replica_count must be non-negative"):
                TiFlashReplica(test_table, replica_count=-1)
        finally:
            test_table.drop(self.client.db_engine, checkfirst=True)


class TestTiFlashReplicaWithTableModel:
    """Test TiFlash replica functionality with TableModel."""

    @pytest.fixture(autouse=True)
    def setup_and_teardown(self, isolated_client: TiDBClient):
        self.client = isolated_client
        yield
        self.client = None

    def _create_test_table(self):
        """Create a test table with a unique name for each test."""
        table_name = generate_dynamic_name("test_tiflash_model_table")

        class Item(TableModel, table=False):
            __tablename__ = table_name
            id: int = Field(primary_key=True)
            name: str
            value: int

        # Create a unique class to avoid SQLAlchemy metadata conflicts
        Item = type(f"Item_{table_name}", (Item,), {})
        table = self.client.create_table(schema=Item, if_exists="overwrite")
        return table, table_name

    def test_create_replica(self):
        table, table_name = self._create_test_table()
        try:
            replica = TiFlashReplica(table._sa_table, replica_count=1)
            replica.create(self.client.db_engine)
            progress = replica.get_replication_progress(self.client.db_engine)
            assert progress["table_name"] == table_name
        finally:
            table._sa_table.drop(self.client.db_engine, checkfirst=True)

    def test_drop_replica(self):
        table, table_name = self._create_test_table()
        try:
            replica = TiFlashReplica(table._sa_table, replica_count=1)
            replica.create(self.client.db_engine)
            replica.drop(self.client.db_engine)
            progress = replica.get_replication_progress(self.client.db_engine)
            assert progress["replica_count"] == 0
        finally:
            table._sa_table.drop(self.client.db_engine, checkfirst=True)

    def test_get_replication_progress(self):
        table, table_name = self._create_test_table()
        try:
            replica = TiFlashReplica(table._sa_table, replica_count=1)
            progress = replica.get_replication_progress(self.client.db_engine)
            assert progress["table_name"] == table_name
            assert isinstance(progress["progress"], float)
        finally:
            table._sa_table.drop(self.client.db_engine, checkfirst=True)

    def test_invalid_replica_count(self):
        table, table_name = self._create_test_table()
        try:
            with pytest.raises(ValueError, match="replica_count must be non-negative"):
                TiFlashReplica(table._sa_table, replica_count=-1)
        finally:
            table._sa_table.drop(self.client.db_engine, checkfirst=True)
