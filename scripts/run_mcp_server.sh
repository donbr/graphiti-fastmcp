#!/bin/bash
# Load environment variables from .env file
set -a
source "$(dirname "$0")/../.env"
set +a

# Run the MCP server
cd "$(dirname "$0")/.."
exec uv run --isolated src/graphiti_mcp_server.py --transport stdio --database-provider neo4j "$@"
