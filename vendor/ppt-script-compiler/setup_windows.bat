@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [1/4] Checking Python...
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py -3"
) else (
  where python >nul 2>nul
  if not %errorlevel%==0 (
    echo Python 3.10 or later is required.
    echo Install Python from https://www.python.org/downloads/windows/
    pause
    exit /b 1
  )
  set "PY=python"
)
%PY% --version

echo [2/4] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv .venv
  if not %errorlevel%==0 exit /b 1
)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if not %errorlevel%==0 (
  echo Python dependency installation failed.
  pause
  exit /b 1
)

echo [3/4] Checking Codex CLI...
where codex >nul 2>nul
if not %errorlevel%==0 (
  where npm >nul 2>nul
  if %errorlevel%==0 (
    echo Codex was not found. Installing with npm...
    call npm install -g @openai/codex
  ) else (
    echo Codex CLI was not found, and npm is unavailable.
    echo Install Codex CLI first, then run this script again.
    echo Official guide: https://developers.openai.com/codex/cli
    pause
    exit /b 1
  )
)
call codex --version

echo [4/4] Checking Codex login...
call codex login status >nul 2>nul
if not %errorlevel%==0 (
  echo.
  echo Codex is installed but not logged in.
  echo Run: codex login
  echo Choose "Sign in with ChatGPT", then return and run start_windows.bat.
) else (
  echo Codex login is ready.
)

echo.
echo Setup complete.
echo Start the tool with start_windows.bat
pause
