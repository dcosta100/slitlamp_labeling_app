@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================
echo   Auto Update (FORCED) - Git + Python venv
echo   (Keeps gitignored local labels)
echo ==========================================
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

REM --- 3) Detect current branch
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

echo Current branch: %BRANCH%
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

REM --- NOTE:
REM We intentionally do NOT run `git clean -fd` here because it can delete
REM untracked AND ignored files (your locally saved labels).
REM If you ever want to clean ONLY non-ignored untracked files safely, you can use:
REM   git clean -fd
REM BUT only if your labels are in a gitignored folder AND you add an exclusion, e.g.:
REM   git clean -fd -e labels/ -e .venv/

REM --- 7) Optional: submodules (safe even if none)
echo.
echo Updating submodules (if any)...
git submodule update --init --recursive
if errorlevel 1 (
  echo [ERROR] submodule update failed.
  goto :FAIL
)

echo.
echo Git update OK.
echo.

REM --- 8) Python environment + requirements
IF EXIST ".venv\Scripts\activate.bat" (
  echo Activating virtual environment...
  call ".venv\Scripts\activate.bat"

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
  echo [WARN] .venv not found. Skipping environment activation.
)

echo.
echo ==========================================
echo   DONE - Repository is up to date
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