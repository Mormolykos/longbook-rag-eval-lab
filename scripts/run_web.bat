@echo off
REM Run the LongBook Verifier local FastAPI web app from the repository root.
cd /d "%~dp0\.."
python -m uvicorn product_mvp.server_longbook_verifier:app --host 127.0.0.1 --port 8078
