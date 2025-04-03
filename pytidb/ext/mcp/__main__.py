import logging

from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import AsyncIterator
from mcp.server.fastmcp import FastMCP, Context
from dataclasses import dataclass

from pytest import Session
from pytidb import TiDBClient

log = logging.getLogger(__name__)

load_dotenv()
tidb_client = TiDBClient.connect()


@dataclass
class AppContext:
    session: Session


@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[AppContext]:
    with tidb_client.session() as session:
        yield AppContext(session=session)


mcp = FastMCP(
    "tidb",
    instructions="""
    you are a tidb database expert, you can help me query, create, and execute sql statements in string on the tidb database.
    Notice:
    - use TiDB instead of MySQL syntax for sql statements
    """,
    lifespan=app_lifespan,
)


@mcp.tool(description="Show all tables in the database")
def show_tables(ctx: Context, db_name: str):
    session: Session = ctx.request_context.lifespan_context.session
    try:
        with tidb_client.session(provided_session=session):
            result = tidb_client.query(f"SHOW TABLES FROM {db_name}").one()
            return result[0]
    except Exception as e:
        log.error(f"Error showing tables: {e}")
        raise e


@mcp.tool(
    description="""
    query the tidb database via sql, best practices:
    - sql is always a string
    - always add LIMIT in the query
    - always add ORDER BY in the query
    """
)
def db_query(ctx: Context, sql: str) -> list[dict]:
    session: Session = ctx.request_context.lifespan_context.session
    try:
        with tidb_client.session(provided_session=session):
            return tidb_client.query(sql).to_list()
    except Exception as e:
        log.error(f"Error querying database: {e}")
        raise e


@mcp.tool(
    description="""
    show create_table sql for a table
    """
)
def show_create_table(ctx: Context, table_name: str) -> str:
    session: Session = ctx.request_context.lifespan_context.session
    try:
        with tidb_client.session(provided_session=session):
            result = session.query(f"SHOW CREATE TABLE {table_name}").one()
            return result[1]
    except Exception as e:
        log.error(f"Error showing create table: {e}")
        raise e


@mcp.tool(
    description="""
    execute sql statments on the sepcific database with TiDB, best practices:
    - sql_stmts is always a string or a list of string
    - always use transaction to execute sql statements
    """
)
def db_execute(ctx: Context, sql_stmts: str | list[str]):
    session: Session = ctx.request_context.lifespan_context.session
    try:
        with tidb_client.session(provided_session=session):
            if isinstance(sql_stmts, str):
                sql = sql_stmts
                session.execute(sql)
            elif isinstance(sql_stmts, list):
                for sql in sql_stmts:
                    session.execute(sql)
        return "success"
    except Exception as e:
        log.error(f"Error executing database: {e}")
        raise e


def get_current_user_prefix() -> str:
    try:
        username = tidb_client.query("SELECT CURRENT_USER()").one()
        if "." in username[0]:
            return username[0].split(".")[0]
        else:
            return ""
    except Exception as e:
        log.error(f"Error getting username prefix: {e}")
        raise e


@mcp.tool(
    description="""
    create a new database user, will return the username with prefix
    """
)
def create_db_user(ctx: Context, username: str, password: str) -> str:
    session: Session = ctx.request_context.lifespan_context.session
    try:
        with tidb_client.session(provided_session=session):
            username_prefix = get_current_user_prefix(ctx)
            full_username = (
                f"{username_prefix}.{username}" if username_prefix else username
            )
            tidb_client.execute(
                f"CREATE USER '{full_username}'@'%' IDENTIFIED BY '{password}'"
            )
            return f"success, username: {full_username}"
    except Exception as e:
        raise e


@mcp.tool(
    description="""
    remove a database user in tidb serverless
    """
)
def remove_db_user(ctx: Context, username: str):
    session: Session = ctx.request_context.lifespan_context.session
    with tidb_client.session(provided_session=session):
        # if user provide a full username, use it directly
        # else get the username prefix and append it to the username
        if "." in username:
            full_username = username
        else:
            username_prefix = get_current_user_prefix()
            full_username = f"{username_prefix}.{username}"
        try:
            tidb_client.execute(f"DROP USER '{full_username}'@'%'")
            return f"success, username: {full_username}"
        except Exception as e:
            raise e


@mcp.tool(
    description="""
    get connection host and port
    """
)
def get_tidb_serverless_address(ctx: Context) -> str:
    return f"{tidb_client.host}:{tidb_client.port}"


if __name__ == "__main__":
    log.info("Starting tidb serverless mcp server...")
    mcp.run(transport="stdio")
