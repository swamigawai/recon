@echo off
setlocal enabledelayedexpansion
title Recon - The Integration Readiness Engine

echo ======================================================================
echo   RECON - ZERO-FRICTION LOCAL LAUNCHER
echo   Automated Environment Verifier, Self-Healer & Web Studio
echo ======================================================================
echo.

:: 1. Verify Python availability in PATH
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python was not detected in your system PATH.
    echo.
    echo To run Recon:
    echo 1. Download and install Python 3.11 or 3.12 from:
    echo    https://www.python.org/downloads/
    echo 2. IMPORTANT: Be sure to check the box:
    echo    "[X] Add python.exe to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Verify Python Version >= 3.11
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Recon requires Python 3.11 or newer.
    for /f "tokens=*" %%v in ('python -c "import sys; print(sys.version.split()[0])"') do echo Currently installed: Python %%v
    echo Please install Python 3.11+ from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

:: 3. Isolated Virtual Environment Setup (.venv)
if not exist ".venv" (
    echo [1/3] Setting up isolated Python virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [WARN] Virtual environment creation was restricted. Falling back to system Python...
    )
)

if exist ".venv\Scripts\python.exe" (
    set "PY_BIN=.venv\Scripts\python.exe"
) else (
    set "PY_BIN=python"
)

:: 4. Verify & Self-Heal Dependencies
echo [2/3] Verifying runtime dependencies and local package...
%PY_BIN% -c "import recon, fastapi, uvicorn, pydantic, multipart" >nul 2>&1
if %errorlevel% neq 0 (
    echo       Installing required dependencies via pip...
    %PY_BIN% -m pip install --upgrade pip --quiet
    %PY_BIN% -m pip install -e . --quiet
    if %errorlevel% neq 0 (
        echo [WARN] Editable install failed; falling back to requirements.txt...
        %PY_BIN% -m pip install -r requirements.txt --quiet
    )
)

:: 5. Launch Recon Web Studio
echo [3/3] Launching Recon Studio...
echo.
%PY_BIN% scripts\fde_launcher.py %*

if %errorlevel% neq 0 (
    echo.
    echo [EXIT] Recon stopped with exit code %errorlevel%.
    pause
)
