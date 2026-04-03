@echo off
setlocal enableextensions

set "ROOT=%~dp0"
for %%I in ("%ROOT%..") do set "ROOT=%%~fI"

echo.
echo [quality] Frontend build
pushd "%ROOT%\frontend"
if errorlevel 1 goto :fail

if not exist "%ROOT%\frontend\node_modules" (
  call npm install --ignore-scripts
  if errorlevel 1 goto :fail_pop_frontend
)

call npm run build
if errorlevel 1 goto :fail_pop_frontend
popd

if /I "%~1"=="--skip-backend" goto :success

echo.
echo [quality] Backend tests
set "PY=python"
if exist "%ROOT%\backend\.venv_sys\Scripts\python.exe" (
  set "PY=%ROOT%\backend\.venv_sys\Scripts\python.exe"
) else if exist "%ROOT%\backend\.venv\Scripts\python.exe" (
  set "PY=%ROOT%\backend\.venv\Scripts\python.exe"
)

pushd "%ROOT%\backend"
if errorlevel 1 goto :fail

"%PY%" -c "import fastapi" >nul 2>nul
if errorlevel 1 (
  echo Skip backend tests: dependencies missing.
  echo Hint: cd backend ^&^& "%PY%" -m pip install -r requirements.txt
  popd
  goto :success
)

"%PY%" -m pytest -q
if errorlevel 1 goto :fail_pop_backend
popd

:success
echo.
echo [quality] Quality gate passed
exit /b 0

:fail_pop_backend
popd
goto :fail

:fail_pop_frontend
popd
goto :fail

:fail
echo.
echo [quality] Quality gate failed
exit /b 1
