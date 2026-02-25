@echo off
cd /d %~dp0

echo =============================
echo Updating repository...
echo =============================

git pull

IF EXIST .venv\Scripts\activate.bat (
    echo.
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat

    IF EXIST requirements.txt (
        echo.
        echo Updating requirements...
        pip install --upgrade pip
        pip install -r requirements.txt
    ) ELSE (
        echo requirements.txt not found.
    )
) ELSE (
    echo .venv not found. Skipping environment activation.
)

echo.
echo Done.
pause