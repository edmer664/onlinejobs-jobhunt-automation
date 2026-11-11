#!/usr/bin/env bash
# MCP Server launcher using stdio transport for AI agents (Claude Desktop, Cursor, Antigravity)
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
    echo "ERROR: Python 3 not found." >&2
    exit 1
fi

export PYTHONUNBUFFERED=1
exec "$PYTHON_BIN" src/mcp_server.py --transport stdio
