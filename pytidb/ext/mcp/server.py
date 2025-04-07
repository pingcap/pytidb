import logging
import mimetypes
import re
import os
from pathlib import Path

from pydantic import AnyUrl
import yaml

from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional
from mcp import Resource
from mcp.server.fastmcp import FastMCP, Context
from dataclasses import dataclass

from pytidb import TiDBClient
from pytidb.utils import TIDB_SERVERLESS_HOST_PATTERN

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger("tidb_mcp_server")

# Load environment variables
load_dotenv()

# Constants
TIDB_SERVERLESS_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+$")

mimetypes.add_type("text/markdown", ".md")


# TiDB Connector
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

    def query(self, sql_stmt: str) -> list[dict]:
        return self.tidb_client.query(sql_stmt).to_list()

    def execute(self, sql_stmts: str | list[str]) -> list[dict]:
        results = []
        with self.tidb_client.session():
            if isinstance(sql_stmts, str):
                result = self.tidb_client.execute(sql_stmts)
                results.append(result.model_dump())
            elif isinstance(sql_stmts, list):
                for stmt in sql_stmts:
                    result = self.tidb_client.execute(stmt)
                    results.append(result.model_dump())
        return results

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


# App Context
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


# MCP Server
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

# Prompts


def parse_markdown_frontmatter(content: str) -> tuple[str, str]:
    """Parse markdown frontmatter and extract title and summary.

    Args:
        content: The markdown content

    Returns:
        A tuple of (title, summary) where title and summary are extracted from frontmatter
        or default values if not found
    """
    title = None
    summary = None

    frontmatter_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if frontmatter_match:
        try:
            frontmatter = yaml.safe_load(frontmatter_match.group(1))
            title = frontmatter.get("title")
            summary = frontmatter.get("summary")
        except yaml.YAMLError:
            pass

    return title, summary


@mcp._mcp_server.list_resources()
async def list_resources() -> list[Resource]:
    log.info("Listing resources...")
    if not os.path.exists("./mcp_resources"):
        return []

    resources = []
    for path in Path("./mcp_resources").rglob("*"):
        if not path.is_file():
            continue

        uri = path.resolve().as_uri()
        filepath = path.as_posix()
        mime_type = mimetypes.guess_type(uri)[0]

        name, description = path.name, None
        if mime_type == "text/markdown":
            with open(filepath, "r") as f:
                content = f.read()
                title, summary = parse_markdown_frontmatter(content)
                name, description = title, summary

        resources.append(
            Resource(uri=uri, name=name, description=description, mimeType=mime_type)
        )

    return resources


@mcp._mcp_server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    log.info(f"Reading resource from {uri}...")

    if uri.scheme != "file":
        raise ValueError(f"Unsupported resource type: {uri}")

    filepath = Path(uri.path).as_posix()
    if os.path.exists(filepath) and "mcp_resources" in filepath:
        with open(filepath, "r") as f:
            return f.read()
    else:
        raise ValueError(f"Can not open the file: {filepath}")


# Tools


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
    
    Note:
    - The user has already specified the database in the configuration, so you don't need to switch 
    database before you execute the sql statements.
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
    Query data from TiDB database via SQL, best practices:
    - using LIMIT for SELECT statements to avoid too many rows returned
    - using db_query to execute SELECT / SHOW / DESCRIBE / EXPLAIN ... read-only statements
    """
)
def db_query(ctx: Context, sql_stmt: str) -> list[dict]:
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        return tidb.query(sql_stmt)
    except Exception as e:
        log.error(f"Failed to execute query sql: {sql_stmt}, error: {e}")
        raise e


@mcp.tool(
    description="""
    Execute operations on TiDB database via SQL, best practices:
    - sql_stmts can be a sql statement string or a list of sql statement strings
    - using db_execute to execute INSERT / UPDATE / DELETE / CREATE / DROP ... statements
    - the sql statements will be executed in the same transaction
    """
)
def db_execute(ctx: Context, sql_stmts) -> list[dict]:
    tidb: TiDBConnector = ctx.request_context.lifespan_context.tidb
    try:
        results = tidb.execute(sql_stmts)
        return results
    except Exception as e:
        log.error(f"Failed to execute operation sqls: sqls: {sql_stmts}, error: {e}")
        raise e


@mcp.tool(
    description="""
    Create a new database user, will return the username with prefix
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
