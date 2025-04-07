# TiDB MCP Server

MCP server implementation for TiDB database.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package installer)

## Installation

Clone the pytidb repository to the local.

```bash
git clone https://github.com/pingcap/pytidb
cd pytidb
```

Install the dependencies.

```bash
uv sync --extra mcp
```

## Configuration

### Environment variables

Go [tidbcloud.com](https://tidbcloud.com) to create a free TiDB database cluster, or use [TiUP Playground](https://docs.pingcap.com/tidb/stable/quick-start-with-tidb/#deploy-a-local-test-cluster) to deploy a local database cluster.

Configuration can be provided through environment variables, or using `.env` file:

- `TIDB_HOST` - TiDB host address, e.g. 'gateway01.us-east-1.prod.aws.tidbcloud.com' ()
- `TIDB_PORT` - TiDB port (default: 4000)
- `TIDB_USERNAME` - Database username, e.g.  'xxxxxxxxxx.\<username\>'
- `TIDB_PASSWORD` - Database password
- `TIDB_DATABASE` - Database name, default is test

### MCP Clients 

#### Claude Desktop

For Claude Desktop users, please check the [quickstart to learn [how to configure mcp server in the Claude Desktop](https://modelcontextprotocol.io/quickstart/user),

In short, you can go to **Settings** dialog, and open the MCP config file by click **Developers > Edit Config**.

Here is an example for `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tidb": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/pytidb",
        "run",
        "--env-file",
        "/path/to/.env",
        "-m",
        "pytidb.ext.mcp"
      ]
    }
  }
}
```

> **Note**
>
> For macOS users, you may need to install the `uv` command globally by command `brew insatll uv`.

#### Cursor

For Cursor users, please check the [Model Context Protocol](https://docs.cursor.com/context/model-context-protocol#configuring-mcp-servers) document to learn how to configure the MCP server in Cursor editor.

In short, you can create a `.cursor/mcp.json` file in your opening project and configure the project-level MCP servers:

Here is an example for `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "tidb": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/path/to/pytidb",
        "--env-file",
        "/path/to/.env",
        "-m",
        "pytidb.ext.mcp"
      ]
    }
  }
}
```
