@echo off
title Corque UI
cd /d "%~dp0"

cd corque-ui
echo Starting Corque UI...
echo.
npm start
if errorlevel 1 (
  echo.
  echo npm start failed.
  pause
  exit /b 1
)
pause
