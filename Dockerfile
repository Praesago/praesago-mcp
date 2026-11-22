FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src

# No dependencies: a stdlib-only stdio bridge to the hosted Praesago MCP server (https://praesago.com/api/mcp).
# Optional: -e PRAESAGO_API_KEY=... for full area context and higher limits.
RUN pip install --no-cache-dir .
ENTRYPOINT ["praesago-mcp"]
