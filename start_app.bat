@echo off
setlocal

set "PROJECT_DIR=%~dp0"
set "PYTHON=%PROJECT_DIR%venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo The project Python environment was not found.
    echo Complete the first-time setup in README.md, then run this file again.
    pause
    exit /b 1
)

start "Resume Parser" "%PYTHON%" "%PROJECT_DIR%app.py"
ping 127.0.0.1 -n 3 >nul
start "" "http://127.0.0.1:5000"
