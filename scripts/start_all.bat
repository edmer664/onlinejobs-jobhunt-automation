@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

REM Resolve Python interpreter (check local venv first)
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_BIN=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_BIN=venv\Scripts\python.exe"
) else (
    set "PYTHON_BIN=python"
)

echo ============================================================
echo  Starting JobHunt OpenSource Web Dashboard + MCP Server
echo  Interpreter: !PYTHON_BIN!
echo  Web UI:      http://localhost:5050
echo  MCP SSE:     http://localhost:5055/sse
echo ============================================================

REM Initialize SQLite database schema
!PYTHON_BIN! -c "from src.db import init_db, DB_PATH; init_db(DB_PATH)"

start "JobHunt Web Dashboard" cmd /k "!PYTHON_BIN! src\app.py"
start "JobHunt MCP Server (SSE)" cmd /k "!PYTHON_BIN! src\mcp_server.py --transport sse --port 5055"

echo Both services launched in dedicated terminal windows!
