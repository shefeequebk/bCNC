@echo off
setlocal

REM === CONFIGURATION ===
set PYTHON_VERSION=3.11
set VENV_NAME=env
set REQUIREMENTS_PATH=bCNC\requirements.txt

echo ===============================
echo Checking for Python %PYTHON_VERSION%
echo ===============================

REM Try to find python3.11 explicitly
where python3.%PYTHON_VERSION:~2% >nul 2>&1
if %errorlevel%==0 (
    for /f "delims=" %%i in ('where python3.%PYTHON_VERSION:~2%') do set "PYTHON_EXEC=%%i"
) else (
    REM Fallback to just 'python'
    for /f "delims=" %%i in ('where python') do set "PYTHON_EXEC=%%i"
)

if not defined PYTHON_EXEC (
    echo ❌ Python %PYTHON_VERSION% is not installed or not in PATH.
    exit /b 1
)

REM Get actual Python version
for /f "tokens=2 delims= " %%v in ('%PYTHON_EXEC% --version') do set "PY_VER=%%v"
echo Found Python version: %PY_VER%

echo %PY_VER% | findstr "^%PYTHON_VERSION%" >nul
if errorlevel 1 (
    echo ❌ Python %PYTHON_VERSION% is required. Found %PY_VER%.
    exit /b 1
)

echo ===============================
echo Creating virtual environment...
echo ===============================
%PYTHON_EXEC% -m venv %VENV_NAME%

if errorlevel 1 (
    echo ❌ Failed to create virtual environment.
    exit /b 1
)

echo ===============================
echo Activating virtual environment...
echo ===============================
call %VENV_NAME%\Scripts\activate.bat

if errorlevel 1 (
    echo ❌ Failed to activate virtual environment.
    exit /b 1
)

echo ===============================
echo Installing requirements...
echo ===============================
pip install --upgrade pip
pip install -r %REQUIREMENTS_PATH%

if errorlevel 1 (
    echo ❌ Failed to install requirements.
    exit /b 1
)

echo ✅ Environment setup complete!
pause
