@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo   Auto Update (FORCED) - Git + Python venv
echo   (Keeps gitignored local labels)
echo ==========================================
echo.

REM --- 0) Stop any running Streamlit BEFORE updating files.
REM     If Streamlit keeps running during the update, Python holds the OLD
REM     .py files in memory and the labeler will not see the new code.
REM     We only kill python.exe processes whose command line contains
REM     "streamlit" (surgical, won't touch unrelated Python apps).
echo Checking for running Streamlit processes...
powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -like '*streamlit*' };" ^
  "if ($p) { $p | ForEach-Object { Write-Host ('  Stopping Streamlit PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force } }" ^
  "else { Write-Host '  No running Streamlit detected.' }"
echo.

REM --- 1) Check if this is a git repo
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [ERROR] This folder is not a git repository.
  goto :FAIL
)

REM --- 2) Check remote "origin"
git remote get-url origin >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Remote "origin" not found.
  echo         Ask Douglas to configure the repo remote.
  goto :FAIL
)

REM --- 3) Detect current branch + record HEAD before the update
for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD') do set "BRANCH=%%B"
if "%BRANCH%"=="" (
  echo [ERROR] Could not detect current branch.
  goto :FAIL
)
if /i "%BRANCH%"=="HEAD" (
  echo [ERROR] Detached HEAD state. Cannot update safely.
  echo         Ask Douglas to checkout a branch (e.g., main).
  goto :FAIL
)
for /f "delims=" %%C in ('git rev-parse --short HEAD') do set "OLD_HEAD=%%C"
echo Branch: %BRANCH%
echo HEAD (before): %OLD_HEAD%
echo.

REM --- 4) Fetch updates
echo Fetching from origin...
git fetch origin --prune
if errorlevel 1 (
  echo [ERROR] git fetch failed.
  goto :FAIL
)

REM --- 5) Verify remote branch exists
git rev-parse --verify "origin/%BRANCH%" >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Remote branch origin/%BRANCH% not found.
  echo         The branch name may differ on the remote.
  goto :FAIL
)

REM --- 6) FORCE sync tracked files to remote (NON-DESTRUCTIVE to gitignored files)
echo.
echo WARNING: This will DISCARD any local changes to TRACKED files.
echo It will NOT delete gitignored files (e.g., local labels).
echo Syncing to origin/%BRANCH% ...
git reset --hard "origin/%BRANCH%"
if errorlevel 1 (
  echo [ERROR] git reset --hard failed.
  goto :FAIL
)

for /f "delims=" %%C in ('git rev-parse --short HEAD') do set "NEW_HEAD=%%C"
echo HEAD (after):  %NEW_HEAD%
if "%OLD_HEAD%"=="%NEW_HEAD%" (
  echo   Already up to date - no commits pulled.
) else (
  echo   Updated %OLD_HEAD% -^> %NEW_HEAD%
)

REM --- NOTE:
REM We intentionally do NOT run `git clean -fd` here because it can delete
REM untracked AND ignored files (your locally saved labels).

REM --- 7) Clear Python bytecode caches so stale .pyc files cannot shadow
REM     the new .py files (defends against clock skew / OneDrive sync quirks).
echo.
echo Clearing __pycache__ directories...
for /d /r %%D in (__pycache__) do (
  if exist "%%D" rmdir /s /q "%%D" 2>nul
)

REM --- 8) Optional: submodules (safe even if none)
echo.
echo Updating submodules (if any)...
git submodule update --init --recursive
if errorlevel 1 (
  echo [ERROR] submodule update failed.
  goto :FAIL
)

REM --- 9) Python environment + requirements
echo.
SET "VENV_DIR="
IF EXIST ".venv\Scripts\activate.bat" SET "VENV_DIR=.venv"
IF NOT DEFINED VENV_DIR IF EXIST "venv\Scripts\activate.bat" SET "VENV_DIR=venv"

IF DEFINED VENV_DIR (
  echo Activating virtual environment ^(!VENV_DIR!^)...
  call "!VENV_DIR!\Scripts\activate.bat"

  IF EXIST "requirements.txt" (
    echo.
    echo Updating Python packages...
    python -m pip install --upgrade pip
    if errorlevel 1 (
      echo [ERROR] pip upgrade failed.
      goto :FAIL
    )

    python -m pip install -r requirements.txt
    if errorlevel 1 (
      echo [ERROR] pip install -r requirements.txt failed.
      goto :FAIL
    )
  ) ELSE (
    echo [WARN] requirements.txt not found. Skipping pip install.
  )
) ELSE (
  echo [WARN] No virtual environment found ^(looked for .venv and venv^).
  echo        Skipping package update. Create one with: python -m venv venv
)

echo.
echo ==========================================
echo   DONE - Repository is at %NEW_HEAD%
echo.
echo   NEXT STEP: run run_streamlit.bat to start the app
echo   (Streamlit was stopped above so it picks up the new code).
echo ==========================================
pause
exit /b 0

:FAIL
echo.
echo ==========================================
echo   UPDATE FAILED
echo ==========================================
echo.
echo Common causes:
echo - No internet / VPN needed
echo - Git not installed or not in PATH
echo - Repo not correctly cloned/configured
echo - Permission issues on this folder
echo.
pause
exit /b 1
