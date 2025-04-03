# TiDB MCP Server

MCP server implementation for TiDB (serverless) database.

## Prerequisites

- uv (Python package installer)

**For MacOS:**

```bash
brew insatll uv
```

## Installation

```bash
# Clone the repository
git clone https://github.com/pingcap/tidb
cd tidb

uv sync --extra[mcp]
```

## Configuration

Go [tidbcloud.com](https://tidbcloud.com) to create a free TiDB database cluster

Configuration can be provided through environment variables, or using `.env`:

- `TIDB_HOST` - TiDB host address, e.g. 'gateway01.us-east-1.prod.aws.tidbcloud.com'
- `TIDB_PORT` - TiDB port (default: 4000)
- `TIDB_USERNAME` - Database username, e.g.  'xxxxxxxxxx.\<username\>'
- `TIDB_PASSWORD` - Database password
- `TIDB_DATABASE` - Database name, default is test

## Run with Claude Desktop

Config Claude Desktop, [HOWTO](https://modelcontextprotocol.io/quickstart/user)

`claude_desktop_config.json`:

```
{
  "mcpServers": {
      "tidb": {
          "command": "uv",
          "args": [
              "--directory",
              "/path/to/pytidb",
              "run",
              "-m",
              "pytidb.ext.mcp"
          ]
      }
  }
}
```
