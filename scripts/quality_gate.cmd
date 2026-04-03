@echo off
setlocal enableextensions enabledelayedexpansion

set "ROOT=%~dp0.."
cd /d "%ROOT%"

echo.
echo [quality] Frontend build
if not exist "%ROOT%\frontend\node_modules" (
  cmd /c "cd /d ""%ROOT%\frontend"" && npm install --ignore-scripts"
  if errorlevel 1 goto :fail
)

cmd /c "cd /d ""%ROOT%\frontend"" && npm run build"
if errorlevel 1 goto :fail

cd /d "%ROOT%"
if /I "%~1"=="--skip-backend" goto :success

echo.
echo [quality] Backend tests
set "PY=python"
if exist "%ROOT%\backend\.venv\Scripts\python.exe" set "PY=%ROOT%\backend\.venv\Scripts\python.exe"

cd /d "%ROOT%\backend"
%PY% -c "import fastapi" >nul 2>nul
if errorlevel 1 (
  echo Skip backend tests: dependencies missing.
  echo Hint: cd backend ^&^& %PY% -m pip install -r requirements.txt
  goto :success
)

%PY% -m pytest -q
if errorlevel 1 goto :fail

:success
echo.
echo [quality] Quality gate passed
exit /b 0

:fail
echo.
echo [quality] Quality gate failed
exit /b 1
