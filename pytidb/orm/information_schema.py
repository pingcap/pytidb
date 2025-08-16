from sqlalchemy import MetaData, Table, Column, String, Integer, Boolean, Float

ischema = MetaData()

tiflash_replica = Table(
    "tiflash_replica",
    ischema,
    Column("TABLE_SCHEMA", String, primary_key=True),
    Column("TABLE_NAME", String, primary_key=True),
    Column("REPLICA_COUNT", Integer),
    Column("LOCATION_LABELS", String),
    Column("AVAILABLE", Boolean),
    Column("PROGRESS", Float),
    schema="INFORMATION_SCHEMA",
)
