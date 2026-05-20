@echo off
title Whisper Dictate
cd /d "%~dp0"

:: Hide the console window after launch
if not "%1"=="silent" (
    start "" /B pythonw dictate.py
    exit
)
python dictate.py