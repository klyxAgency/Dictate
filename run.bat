@echo off
title Whisper Dictate
cd /d C:\dictate-app

:: Hide the console window after launch
if not "%1"=="silent" (
    start "" /B pythonw dictate.py
    exit
)
python dictate.py