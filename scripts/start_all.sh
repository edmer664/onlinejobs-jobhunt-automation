#!/usr/bin/env bash
# Dual-process launcher for JobHunt Web Dashboard (5050) and MCP SSE Server (5055)
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

# Resolve Python interpreter (prefer virtual environment)
if [ -f "$ROOT_DIR/.venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
elif [ -f "$ROOT_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$ROOT_DIR/venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
else
    echo "ERROR: Python 3 interpreter not found. Please install Python 3.12+." >&2
    exit 1
fi

echo "============================================================"
echo " Starting JobHunt OpenSource Web Dashboard + MCP Server"
echo " Interpreter: $PYTHON_BIN"
echo " Web UI:      http://localhost:5050"
echo " MCP SSE:     http://localhost:5055/sse"
echo "============================================================"

# Ensure SQLite schema is initialized
"$PYTHON_BIN" -c "from src.db import init_db, DB_PATH; init_db(DB_PATH)"

# Trap signals for graceful shutdown
cleanup() {
    echo ""
    echo "Shutting down JobHunt services..."
    if [ -n "$APP_PID" ] && kill -0 "$APP_PID" 2>/dev/null; then
        kill "$APP_PID" 2>/dev/null || true
    fi
    if [ -n "$MCP_PID" ] && kill -0 "$MCP_PID" 2>/dev/null; then
        kill "$MCP_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo "Services stopped cleanly."
}
trap cleanup SIGINT SIGTERM EXIT

# Launch Web Dashboard
"$PYTHON_BIN" src/app.py &
APP_PID=$!

# Launch MCP Server in SSE transport mode
"$PYTHON_BIN" src/mcp_server.py --transport sse --port 5055 &
MCP_PID=$!

echo "Dashboard running with PID: $APP_PID"
echo "MCP Server running with PID: $MCP_PID"
echo "Press Ctrl+C to terminate both services."

wait
