@echo off
cd /d "I:\website cloner"
title Website Reference Analyzer
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
  start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" "http://127.0.0.1:8010"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
  start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" "http://127.0.0.1:8010"
) else (
  start "" chrome "http://127.0.0.1:8010"
)
python -m uvicorn main:app --host 127.0.0.1 --port 8010
pause
