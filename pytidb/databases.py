from sqlalchemy import Engine, text
from typing import Optional, Literal

from pytidb.utils import run_sync


def create_database(
    db_engine: Engine,
    name: str,
    if_exists: Optional[Literal["raise", "skip"]] = "raise",
):
    if if_exists not in ["raise", "skip"]:
        raise ValueError(f"Invalid if_exists value: {if_exists}")

    identifier_preparer = db_engine.dialect.identifier_preparer
    db_name = identifier_preparer.quote(name)
    with db_engine.connect() as conn:
        if if_exists == "skip":
            stmt = text(f"CREATE DATABASE IF NOT EXISTS {db_name};")
        else:
            stmt = text(f"CREATE DATABASE {db_name};")
        return conn.execute(stmt)


def database_exists(db_engine: Engine, name: str) -> bool:
    stmt = text(
        "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :db_name;"
    )
    with db_engine.connect() as conn:
        result = conn.execute(stmt, {"db_name": name})
        return bool(result.scalar())


async def create_database_async(
    db_engine: Engine,
    name: str,
    if_exists: Optional[Literal["raise", "skip"]] = "raise",
):
    """Async wrapper around :func:`create_database`."""

    return await run_sync(create_database, db_engine, name, if_exists=if_exists)


async def database_exists_async(db_engine: Engine, name: str) -> bool:
    """Async wrapper around :func:`database_exists`."""

    return await run_sync(database_exists, db_engine, name)
