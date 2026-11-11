#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

echo "============================================================"
echo " Starting JobHunt OpenSource Web Dashboard + MCP Server"
echo " Web UI:  http://localhost:5050"
echo " MCP SSE: http://localhost:5055/sse"
echo "============================================================"

# Trap SIGINT and SIGTERM to kill background children
trap 'kill $(jobs -p)' SIGINT SIGTERM EXIT

python src/app.py &
APP_PID=$!

python src/mcp_server.py --transport sse --port 5055 &
MCP_PID=$!

echo "Dashboard running with PID: $APP_PID"
echo "MCP Server running with PID: $MCP_PID"

wait
