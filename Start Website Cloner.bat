@echo off
cd /d "%~dp0"
title Website Cloner
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Project environment missing. Create .venv and install requirements.txt first.
  pause
  exit /b 1
)
start "" "http://127.0.0.1:8010"
"%~dp0.venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8010
pause
