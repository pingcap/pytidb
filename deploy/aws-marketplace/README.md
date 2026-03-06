# Publish TiDB MCP Server to AWS Marketplace

This folder contains the baseline assets to package this repository's MCP server as an AWS Marketplace AI tool.

## Requirements

- Python >= 3.10
- MCP Python SDK >= 1.26.0 (installed via `pip install ".[mcp]"`)

## What this package does

- Runs `tidb-mcp-server` in `streamable-http` mode
- Binds to `0.0.0.0:8000`
- Exposes MCP endpoint at `POST /mcp`
- Uses stateless HTTP with MCP-compatible responses (`application/json` or `text/event-stream`)


## 1) Build the container image

Ensure you have the MCP dependencies available (defined in `pyproject.toml` under `[project.optional-dependencies]`):

```bash
docker build -f deploy/aws-marketplace/Dockerfile -t tidb-mcp-server:marketplace .
```

## 2) Run a local smoke test

```bash
docker run --rm -p 8000:8000 \
  -e TIDB_HOST='<your-tidb-host>' \
  -e TIDB_PORT='4000' \
  -e TIDB_USERNAME='root' \
  -e TIDB_PASSWORD='' \
  -e TIDB_DATABASE='test' \
  tidb-mcp-server:marketplace
```

The container runs with `--transport streamable-http --host 0.0.0.0 --port 8000` by default.
`/mcp` path and stateless mode are fixed for predictable Marketplace behavior.

In another terminal, call the MCP endpoint:

```bash
# Initialize the MCP session
curl -i -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": "1",
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {"name": "smoke-test", "version": "0.1.0"}
    }
  }'
```

The server will return MCP-compliant JSON responses.

## 3) Push image to Amazon ECR

```bash
AWS_ACCOUNT_ID='<your-account-id>'
AWS_REGION='us-east-1'
ECR_REPO='tidb-mcp-server'

aws ecr create-repository --repository-name "${ECR_REPO}" --region "${AWS_REGION}" || true
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

docker tag tidb-mcp-server:marketplace "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:v1"
docker push "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:v1"
```

## 4) Create the AWS Marketplace listing

In AWS Marketplace Management Portal, create an **AI Agents and Tools** product with **Container-based AI agent** delivery.

Use these runtime values:

- Protocol: MCP `streamable-http`
- Mode: `stateless`
- Endpoint path: `/mcp`
- HTTP method: `POST`
- Container listen address: `0.0.0.0:8000`

Then provide:

- Container image URI from ECR
- Deployment template/runtime details (typically ECS/EKS)
- Usage instructions and required environment variables (`TIDB_HOST`, `TIDB_PORT`, `TIDB_USERNAME`, `TIDB_PASSWORD`, `TIDB_DATABASE`)

## 5) Pre-submission checklist

- The image starts with no manual bootstrap steps.
- `POST /mcp` is reachable and returns valid MCP responses.
- Service runs in stateless mode.
- Documentation explains required TiDB credentials and network access.
- Metering/pricing dimensions are configured in the listing.

## References

- AWS Marketplace: [AI agents and tools product type](https://docs.aws.amazon.com/marketplace/latest/userguide/ai-agents-and-tools.html)
- AWS Marketplace: [Container listing overview](https://docs.aws.amazon.com/marketplace/latest/userguide/container-product-policies.html)
- AWS Marketplace: [Publish a container product](https://docs.aws.amazon.com/marketplace/latest/userguide/container-product-getting-started.html)
- AWS Marketplace MCP requirements: [Technical requirements for AI agents and tools](https://docs.aws.amazon.com/marketplace/latest/userguide/ai-agents-tools-tech-requirements.html)
- MCP Python SDK (`streamable-http`): [FastMCP transport examples](https://github.com/modelcontextprotocol/python-sdk)
- MCP Python SDK examples: [stateless streamable-http server](https://github.com/modelcontextprotocol/python-sdk/tree/main/examples/servers/simple-streamablehttp-stateless)
- Elastic MCP server reference: [mcp-server-elasticsearch](https://github.com/elastic/mcp-server-elasticsearch)
