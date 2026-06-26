@echo off
REM Launch the LongBook Verifier local stdio MCP server from the repository root.
REM Requires the `mcp` package: python -m pip install mcp
cd /d "%~dp0\.."
python product_mvp\mcp_longbook_server.py
