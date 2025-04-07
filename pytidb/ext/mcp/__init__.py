from typing import Literal

import click

from pytidb.ext.mcp.server import mcp, log


@click.command()
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="stdio",
    help="Transport type",
)
def main(transport: Literal["stdio", "sse"] = "stdio"):
    log.info("Starting tidb mcp server...")
    mcp.run(transport=transport)
