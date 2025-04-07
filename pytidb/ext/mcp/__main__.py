import logging
import re

from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from mcp.server.fastmcp import FastMCP, Context
from dataclasses import dataclass

from pytidb import TiDBClient
from pytidb.utils import TIDB_SERVERLESS_HOST_PATTERN

log = logging.getLogger(__name__)

load_dotenv()

TIDB_SERVERLESS_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$")


class TiDBConnector:
    def __init__(
        self,
        database_url: Optional[str] = None,
        *,
        host: Optional[str] = "127.0.0.1",
        port: Optional[int] = 4000,
        username: Optional[str] = "root",
        password: Optional[str] = "",
        database: Optional[str] = "test",
    ):
        self.tidb_client = TiDBClient.connect(
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.is_tidb_serverless = TIDB_SERVERLESS_HOST_PATTERN.match(host)

    def show_databases(self) -> list[dict]:
        return self.tidb_client.query("SHOW DATABASES").to_list()

    def switch_database(
        self,
        db_name: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.tidb_client = TiDBClient.connect(
            host=self.host,
            port=self.port,
            username=username or self.username,
            password=password or self.password,
            database=db_name or self.database,
        )

    def show_tables(self) -> list[str]:
        return self.tidb_client.table_names()

    def query(self, sql: str) -> list[dict]:
        return self.tidb_client.query(sql).to_list()

    def execute(self, sql: str | list[str]) -> None:
        with self.tidb_client.session():
            if isinstance(sql, str):
                self.tidb_client.execute(sql)
            elif isinstance(sql, list):
                for stmt in sql:
                    self.tidb_client.execute(stmt)

    def is_tidb_serverless(self) -> bool:
        return TIDB_SERVERLESS_HOST_PATTERN.match(self.host)

    def current_username(self) -> str:
        return self.tidb_client.query("SELECT CURRENT_USER()").scalar()

    def current_username_prefix(self) -> str:
        current_username = self.current_username()
        if TIDB_SERVERLESS_USERNAME_PATTERN.match(current_username):
            return current_username.split(".")[0]
        else:
            return current_username

    def create_user(self, username: str, password: str) -> str:
        if self.is_tidb_serverless:
            if not TIDB_SERVERLESS_USERNAME_PATTERN.match(username):
                username = f"{self.current_username_prefix()}.{username}"

        self.tidb_client.execute(
            "CREATE USER :username IDENTIFIED BY :password",
            {
                "username": username,
                "password": password,
            },
        )
        return username

    def remove_user(self, username: str) -> None:
        # Auto append the username prefix for tidb serverless.
        if self.is_tidb_serverless:
            if not TIDB_SERVERLESS_USERNAME_PATTERN.match(username):
                username = f"{self.current_username_prefix()}.{username}"

        self.tidb_client.execute(
            "DROP USER :username",
            {
                "username": username,
            },
            raise_error=True,
        )

    def disconnect(self) -> None:
        self.tidb_client.disconnect()


@dataclass
class AppContext:
    tidb: TiDBConnector


@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[AppContext]:
    log.info("Starting TiDB Connector...")
    tidb = TiDBConnector()
    try:
        yield AppContext(tidb=tidb)
    finally:
        tidb.disconnect()


mcp = FastMCP(
    "tidb",
    instructions="""You are a tidb database expert, you can help me query, create, and execute sql 
statements on the tidb database.

Notice:
- use TiDB instead of MySQL syntax for sql statements
- use switch_database tool only if there's explicit instruction, you can reference different databases 
via the `<db_name>.<table_name>` syntax.
    """,
    lifespan=app_lifespan,
)


@mcp.tool(description="Show all databases in the tidb cluster")
def show_databases(ctx: Context) -> list[dict]:
    tidb = ctx.request_context.lifespan_context.tidb
    try:
        return tidb.show_databases()
    except Exception as e:
        log.error(f"Failed to show databases: {e}")
        raise e


@mcp.tool(
    description="""
    Switch to a specific database.
    """
)
def switch_database(
    ctx: Context,
    db_name: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> None:
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        tidb.switch_database(db_name, username, password)
    except Exception as e:
        log.error(f"Failed to switch database to {db_name}: {e}")
        raise e


@mcp.tool(description="Show all tables in the database")
def show_tables(ctx: Context) -> list[str]:
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        return tidb.show_tables()
    except Exception as e:
        log.error(f"Failed to show tables for database {tidb.database}: {e}")
        raise e


@mcp.tool(
    description="""
    Query the TiDB database via SQL, best practices:
    - sql is always a SQL statement string
    - always add LIMIT in the query
    - always add ORDER BY in the query
    - The query result of SELECT / SHOW / DESCRIBE / EXPLAIN / ... will be returned as a list of dicts
    """
)
def db_query(ctx: Context, sql: str) -> list[dict]:
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        return tidb.query(sql)
    except Exception as e:
        log.error(f"Failed to execute query {sql}: {e}")
        raise e


@mcp.tool(
    description="""
    Execute sql statements, best practices:
    - sql_stmts is always a sql statement string or a list of sql statement strings
    - The sql statements will be executed in a same transaction
    """
)
def db_execute(ctx: Context, sql_stmts: str | list[str]):
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        tidb.execute(sql_stmts)
        return "success"
    except Exception as e:
        log.error(f"Failed to execute sql statements: {e}")
        raise e


@mcp.tool(
    description="""
    create a new database user, will return the username with prefix
    """
)
def db_create_user(ctx: Context, username: str, password: str) -> str:
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        fullname = tidb.create_user(username, password)
        return f"success, username: {fullname}"
    except Exception as e:
        log.error(f"Failed to create database user {username}: {e}")
        raise e


@mcp.tool(
    description="""
    Remove a database user in TiDB cluster.
    """
)
def db_remove_user(ctx: Context, username: str):
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        tidb.remove_user(username)
        return f"success, deleted user with username {username}"
    except Exception as e:
        log.error(f"Failed to remove database user {username}: {e}")
        raise e


if __name__ == "__main__":
    log.info("Starting tidb mcp server...")
    mcp.run(transport="stdio")
