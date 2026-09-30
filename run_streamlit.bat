@echo off
title Streamlit — Slitlamp App

REM Go to project root (where this .bat lives)
cd /d "%~dp0" || (
    echo Failed to change directory
    pause
    exit /b
)

REM Activate the virtual environment. Accept either name: this repo has
REM historically used "venv", while these scripts used to look only for
REM ".venv" and would exit before ever starting Streamlit.
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo Virtual environment not found ^(looked for .venv and venv^).
    echo Create one with:  python -m venv venv
    pause
    exit /b
)

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
