@echo off
title Whisper Dictate - Stop
echo Stopping Whisper Dictate...
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
echo Done!
ping 127.0.0.1 -n 3 >nul
