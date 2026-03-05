FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY pyproject.toml README.md LICENSE ./
COPY pytidb ./pytidb

RUN pip install --upgrade pip && pip install ".[mcp]"

USER app

EXPOSE 8000

# Run in streamable-http mode on 0.0.0.0:8000 for AWS Marketplace
CMD ["tidb-mcp-server", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
