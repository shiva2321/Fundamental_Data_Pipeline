@echo off
REM Fundamental Data Pipeline - Desktop Application Launcher
REM This script launches the PyQt5 desktop application

echo.
echo ========================================
echo Fundamental Data Pipeline - Desktop App
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install/update requirements
echo Installing required packages...
pip install -q -r requirements.txt

REM Launch the application
echo Launching desktop application...
python app.py

pause

