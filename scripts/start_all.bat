@echo off
cd /d "%~dp0.."
echo ============================================================
echo  Starting JobHunt OpenSource Web Dashboard + MCP Server
echo  Web UI:  http://localhost:5050
echo  MCP SSE: http://localhost:5055/sse
echo ============================================================
start "JobHunt Web Dashboard" cmd /k "python src\app.py"
start "JobHunt MCP Server (SSE)" cmd /k "python src\mcp_server.py --transport sse --port 5055"
echo All services launched!
