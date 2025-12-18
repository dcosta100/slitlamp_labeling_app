@echo off
title Streamlit — Slitlamp App

REM Go to project root (where this .bat lives)
cd /d "%~dp0" || (
    echo Failed to change directory
    pause
    exit /b
)

REM Activate venv
if not exist venv\Scripts\activate (
    echo Virtual environment not found.
    pause
    exit /b
)
call venv\Scripts\activate

REM Start Streamlit in background
start "" cmd /c "streamlit run app.py --server.port 8501"

REM Wait for server to be up
echo Waiting for Streamlit to start...
:waitloop
timeout /t 1 >nul
powershell -Command ^
    "try { (Invoke-WebRequest http://localhost:8501 -UseBasicParsing).StatusCode -eq 200 } catch { exit 1 }" ^
    && goto openbrowser
goto waitloop

:openbrowser
start http://localhost:8501
exit /b
