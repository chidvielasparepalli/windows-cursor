@echo off
setlocal
cd /d "%~dp0"

if not exist "aircursor_runtime.pyc" (
  echo ERROR: AirCursor runtime is missing.
  echo The repository currently contains only the launcher, not the runtime.
  echo Restore aircursor_runtime.pyc from a trusted project release before running.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  python -m venv .venv
  if errorlevel 1 goto :error
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 goto :error
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 goto :error
)

".venv\Scripts\python.exe" aircursor.py
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo AirCursor setup or launch failed. See the error above.
pause
exit /b 1
