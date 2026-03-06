from typing import Literal

import click
import logging

from pytidb.ext.mcp.server import create_mcp_server, log


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    envvar="TIDB_MCP_TRANSPORT",
    show_default=True,
    help="Transport type",
)
@click.option(
    "--host",
    default="127.0.0.1",
    envvar="TIDB_MCP_HOST",
    show_default=True,
    help="Host to bind for network transports",
)
@click.option(
    "--port",
    type=int,
    default=8000,
    envvar="TIDB_MCP_PORT",
    show_default=True,
    help="Port to bind for network transports",
)
def main(
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    log.info("Starting tidb mcp server...")

    # Create MCP server with custom configuration
    stateless = transport == "streamable-http"
    mcp = create_mcp_server(
        host=host,
        port=port,
        stateless_http=stateless,
    )
    mcp.run(transport=transport)
