from typing import Optional, Any, TypedDict
from sqlalchemy.sql.schema import SchemaItem
from sqlalchemy.sql.base import DialectKWArgs
from sqlalchemy.sql.ddl import _CreateBase
from sqlalchemy import Connection, Engine, select, Table
from pytidb.orm._typing import _CreateDropBind
from .information_schema import tiflash_replica


class TiFlashReplicaProgress(TypedDict):
    table_schema: str
    table_name: str
    replica_count: int
    location_labels: str
    available: bool
    progress: float


class SetTiFlashReplica(_CreateBase):
    """DDL element for SET TIFLASH REPLICA operation."""

    __visit_name__ = "set_tiflash_replica"

    def __init__(self, element):
        super().__init__(element)


class TiFlashReplica(DialectKWArgs, SchemaItem):
    """A table-level TiFlash replica.

    TiFlash is the columnar storage engine for TiDB. This class provides
    DDL operations to manage TiFlash replicas for tables.

    Examples::

        # Create TiFlash replica
        replica = TiFlashReplica(table, replica_count=2)
        replica.create(engine)

        # Drop TiFlash replica
        replica.drop(engine)

        # Check replication progress
        progress = replica.get_replication_progress(engine)

    """

    __visit_name__ = "tiflash_replica"

    def __init__(
        self,
        table: "Table",
        replica_count: int = 1,
        quote: Optional[bool] = None,
        info: Optional[dict] = None,
        **dialect_kw: Any,
    ) -> None:
        """Construct a TiFlash replica object.

        :param table: The table to configure TiFlash replicas for
        :param replica_count: Number of replicas to create (0 to remove all replicas)
        :param quote: Whether to apply quoting to table name
        :param info: Optional data dictionary
        :param **dialect_kw: Additional dialect-specific keyword arguments
        """
        if replica_count < 0:
            raise ValueError("replica_count must be non-negative")

        self.table = table
        self.replica_count = replica_count

        if info is not None:
            self.info = info

        self._validate_dialect_kwargs(dialect_kw)

    def create(self, bind: _CreateDropBind) -> None:
        """Issue an ``ALTER TABLE ... SET TIFLASH REPLICA`` statement for this
        :class:`.TiFlashReplica`, using the given
        :class:`.Connection` or :class:`.Engine`` for connectivity.

        .. seealso::

            :meth:`_schema.MetaData.create_all`.
        """
        from pytidb.orm.sql.ddl import TiDBSchemaGenerator

        bind._run_ddl_visitor(TiDBSchemaGenerator, self)

    def drop(self, bind: _CreateDropBind) -> None:
        """Issue an ``ALTER TABLE ... SET TIFLASH REPLICA 0`` statement for this
        :class:`.TiFlashReplica`, using the given
        :class:`.Connection` or :class:`.Engine`` for connectivity.

        .. seealso::

            :meth:`_schema.MetaData.drop_all`.
        """
        from pytidb.orm.sql.ddl import TiDBSchemaDropper

        bind._run_ddl_visitor(TiDBSchemaDropper, self)

    def get_replication_progress(self, bind: _CreateDropBind) -> TiFlashReplicaProgress:
        """Check TiFlash replication progress for the table.

        :param bind: Connection or Engine for connectivity
        :return: Dictionary with replication status information
        """

        if isinstance(bind, Connection):
            connection = bind
            schema_name = bind.engine.url.database
        elif isinstance(bind, Engine):
            connection = bind.connect()
            schema_name = bind.url.database

        try:
            table_name = self.table.name

            query = select(tiflash_replica).where(
                tiflash_replica.c.TABLE_SCHEMA == schema_name,
                tiflash_replica.c.TABLE_NAME == table_name,
            )
            result = connection.execute(query)
            row = result.fetchone()

            if row:
                return {
                    "table_schema": row.TABLE_SCHEMA,
                    "table_name": row.TABLE_NAME,
                    "replica_count": row.REPLICA_COUNT,
                    "location_labels": row.LOCATION_LABELS,
                    "available": bool(row.AVAILABLE),
                    "progress": float(row.PROGRESS)
                    if row.PROGRESS is not None
                    else 0.0,
                }
            else:
                return {
                    "table_schema": schema_name,
                    "table_name": table_name,
                    "replica_count": 0,
                    "location_labels": "",
                    "available": False,
                    "progress": 0.0,
                }
        finally:
            if hasattr(bind, "connect"):
                connection.close()

    def __repr__(self) -> str:
        return f"TiFlashReplica({self.table.name}, replica_count={self.replica_count})"
