@echo off
cd /d "%~dp0.."

REM Resolve Python interpreter
if exist ".venv\Scripts\python.exe" (
    set "PYTHON_BIN=.venv\Scripts\python.exe"
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_BIN=venv\Scripts\python.exe"
) else (
    set "PYTHON_BIN=python"
)

set PYTHONUNBUFFERED=1
"!PYTHON_BIN!" src\mcp_server.py --transport stdio
