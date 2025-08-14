from typing import Optional, Any, TYPE_CHECKING, Union
from sqlalchemy.sql.schema import SchemaItem
from sqlalchemy.sql.base import DialectKWArgs
from sqlalchemy import text
from pytidb.orm.sql.ddl import TiDBSchemaGenerator

if TYPE_CHECKING:
    from sqlalchemy import Table, Engine, Connection

_CreateDropBind = Union["Engine", "Connection"]


class SetTiFlashReplica:
    """DDL element for SET TIFLASH REPLICA operation."""

    __visit_name__ = "set_tiflash_replica"

    def __init__(self, table: "Table", replica_count: int):
        self.table = table
        self.replica_count = replica_count


class TiFlashReplica(DialectKWArgs, SchemaItem):
    """A table-level TiFlash replica configuration.

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

    def create(self, bind: _CreateDropBind, checkfirst: bool = False) -> None:
        """Issue an ``ALTER TABLE ... SET TIFLASH REPLICA`` statement.

        :param bind: Connection or Engine for connectivity
        :param checkfirst: If True, check if operation is needed before executing
        """
        set_replica = SetTiFlashReplica(self.table, self.replica_count)
        bind._run_ddl_visitor(TiDBSchemaGenerator, set_replica, checkfirst=checkfirst)

    def drop(self, bind: _CreateDropBind, checkfirst: bool = False) -> None:
        """Remove TiFlash replicas by setting replica count to 0.

        :param bind: Connection or Engine for connectivity
        :param checkfirst: If True, check if operation is needed before executing
        """
        set_replica = SetTiFlashReplica(self.table, 0)
        bind._run_ddl_visitor(TiDBSchemaGenerator, set_replica, checkfirst=checkfirst)

    def get_replication_progress(self, bind: _CreateDropBind) -> dict:
        """Check TiFlash replication progress for the table.

        :param bind: Connection or Engine for connectivity
        :return: Dictionary with replication status information
        """
        if hasattr(bind, "execute"):
            connection = bind
        else:
            connection = bind.connect()

        try:
            schema_name = (
                self.table.schema
                or connection.execute(text("SELECT DATABASE()")).scalar()
            )
            table_name = self.table.name

            query = text("""
            SELECT TABLE_SCHEMA, TABLE_NAME, REPLICA_COUNT, LOCATION_LABELS, 
                   AVAILABLE, PROGRESS
            FROM information_schema.tiflash_replica 
            WHERE TABLE_SCHEMA = :schema_name AND TABLE_NAME = :table_name
            """)

            result = connection.execute(
                query, {"schema_name": schema_name, "table_name": table_name}
            )
            row = result.fetchone()

            if row:
                return {
                    "table_schema": row[0],
                    "table_name": row[1],
                    "replica_count": row[2],
                    "location_labels": row[3],
                    "available": bool(row[4]),
                    "progress": float(row[5]) if row[5] is not None else 0.0,
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
