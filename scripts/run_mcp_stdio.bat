@echo off
cd /d "%~dp0.."
python src\mcp_server.py --transport stdio
