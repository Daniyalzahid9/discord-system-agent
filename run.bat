@echo off
title Discord System Agent
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo [!] Activating virtual environment...
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found in .venv.
    pause
    exit /b 1
)

echo [*] Starting Discord System Controller Bot...
".venv\Scripts\python.exe" bot.py
pause
