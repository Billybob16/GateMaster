@echo off
title GateMaster Startup
echo ============================================
echo        STARTING GATEMASTER BACKEND
echo ============================================

REM Move to script directory
cd /d "%~dp0"

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Set Flask app
set FLASK_APP=src/app.py

echo Starting Flask server...
flask run --host=0.0.0.0 --port=5000
