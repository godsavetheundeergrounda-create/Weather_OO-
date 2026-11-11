@echo off
setlocal EnableExtensions

rem Run from the repository directory, regardless of the caller's current folder.
cd /d "%~dp0"
if errorlevel 1 goto directory_error

rem Use UTF-8 for Python/pip output. Launcher messages are ASCII for CMD compatibility.
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "INSTALL_MARKER=%CD%\.venv\.weather-aggregator-installed"
set "LOG_FILE=%CD%\weather-aggregator-startup.log"
set "EXIT_CODE=0"

title Weather Aggregator

echo ========================================
echo        WEATHER AGGREGATOR - START
echo ========================================
echo.

if exist "%VENV_PYTHON%" goto check_python

echo [1/2] Creating Python virtual environment...
where py >nul 2>&1
if not errorlevel 1 goto create_with_py
where python >nul 2>&1
if not errorlevel 1 goto create_with_python
goto no_python

:create_with_py
py -3 -m venv ".venv" > "%LOG_FILE%" 2>&1
if errorlevel 1 goto venv_error
goto check_python

:create_with_python
python -m venv ".venv" > "%LOG_FILE%" 2>&1
if errorlevel 1 goto venv_error
goto check_python

:check_python
"%VENV_PYTHON%" -c "import sys; raise SystemExit(sys.version_info < (3, 10))" >nul 2>&1
if errorlevel 1 goto wrong_python

if not exist "%INSTALL_MARKER%" goto install_dependencies
"%VENV_PYTHON%" -c "import weather_aggregator, fastapi, aiohttp, uvicorn" >nul 2>&1
if errorlevel 1 del /q "%INSTALL_MARKER%" >nul 2>&1
if exist "%INSTALL_MARKER%" goto run_server

:install_dependencies
echo [2/2] Installing project and dependencies (first run)...
echo This may take a few minutes. Details will be saved to:
echo %LOG_FILE%
echo.
"%VENV_PYTHON%" -m pip install --disable-pip-version-check -e . > "%LOG_FILE%" 2>&1
if errorlevel 1 goto install_error
type nul > "%INSTALL_MARKER%"

goto run_server

:run_server
echo.
echo Starting Weather Aggregator...
echo Your browser should open at http://localhost:8000
echo To stop the server, press Ctrl+C.
echo.
"%VENV_PYTHON%" -m weather_aggregator.web %*
set "EXIT_CODE=%ERRORLEVEL%"
if "%EXIT_CODE%"=="0" goto stopped

echo.
echo ERROR: The web server stopped with exit code %EXIT_CODE%.
echo Check the messages above for details.
goto finish

:stopped
echo.
echo The web server has stopped.
goto finish

:no_python
echo ERROR: Python 3.10 or newer was not found.
echo Install Python from https://www.python.org/downloads/ and try again.
set "EXIT_CODE=1"
goto finish

:wrong_python
echo ERROR: This project requires Python 3.10 or newer.
echo Detected version:
"%VENV_PYTHON%" --version
set "EXIT_CODE=1"
goto finish

:venv_error
echo ERROR: Could not create the virtual environment.
echo Installer output:
if exist "%LOG_FILE%" type "%LOG_FILE%"
set "EXIT_CODE=1"
goto finish

:install_error
echo ERROR: Dependency installation failed.
echo Check your internet connection and Python installation.
echo Full installer output:
if exist "%LOG_FILE%" type "%LOG_FILE%"
set "EXIT_CODE=1"
goto finish

:directory_error
echo ERROR: Could not open the project directory.
set "EXIT_CODE=1"
goto finish

:finish
echo.
echo ========================================
echo Launcher finished. This window will stay open.
echo Press any key to close this window...
echo ========================================
pause >nul
exit /b %EXIT_CODE%
