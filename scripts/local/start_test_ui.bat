@echo off
cd /d "%~dp0..\.."
chcp 65001 >nul

echo =========================================
echo   Agentic Calorie Assistant - Test UI
echo =========================================
echo.

:: Kill any leftover process on port 8011
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr "LISTENING" ^| findstr ":8011 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Starting server...
start "Canary Server" cmd.exe /k "cd /d "%~dp0" && uvicorn app.main:app --host 127.0.0.1 --port 8011 --reload"

echo Waiting 3 seconds for server...
timeout /t 3 /nobreak >nul

echo Opening browser...
start "" http://127.0.0.1:8011/

echo.
echo Done! Close the "Canary Server" window to stop.
timeout /t 3 >nul
