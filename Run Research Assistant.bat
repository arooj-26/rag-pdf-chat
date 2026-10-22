@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating the project Python environment...
    python -m venv .venv
    if errorlevel 1 goto failed
    ".venv\Scripts\python.exe" -m pip install -r requirements.lock
    if errorlevel 1 goto failed
)

".venv\Scripts\python.exe" scripts\start_local.py
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo Startup failed. Review the message above.
pause
exit /b 1
